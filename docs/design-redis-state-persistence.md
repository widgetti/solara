# Design: opt-in reactive state persistence to Redis

**Status:** proposal, revision 2 — after a 5-persona adversarial review round
(distributed-systems, maintainer/scope, security, app-developer DX, SRE) on top of the
original 4 investigation reviews. Revision 2 fixes four confirmed blockers (see §12).
**Date:** 2026-07-02
**Problem owner:** solara-server

## 1. Problem and goals

Solara is stateful: each browser tab owns a virtual kernel holding the widget tree,
reactive values, and hook state. Behind a load balancer, a websocket reconnect can land
on a different instance. That instance has no kernel for the client's kernel id, and the
client shows the blocking "Could not restore session. Please refresh." dialog — all
state is lost.

**Goals**

1. A reconnect that lands on a different instance recovers transparently: no refresh
   dialog, no page reload, opted-in state intact.
2. State is persisted **opt-in, per reactive variable**. Most state is derived or cheaply
   recoverable from a database; much of it does not serialize well or efficiently. The
   author declares what matters.
3. Write on change (debounced), read on connect. Redis is a recovery cache, not a
   database: when Redis is down, Solara degrades to exactly today's behavior.
4. Production-grade: no new blocking I/O on the interaction path, bounded failure modes,
   observable, secure.

**Non-goals (v1)**

- Persisting `use_state` / component-local `use_reactive` (no stable cross-process key;
  keys are render-tree-position or creation-order dependent).
- Persisting `Computed` (derived — must recompute) or `Singleton` (per-kernel resources).
- Surviving a browser refresh (F5 generates a new kernel id; session-scoped storage is a
  separate future feature, cf. NiceGUI `user` storage).
- Cross-tab shared state, full session migration, live kernel handoff.

## 2. Current architecture (verified)

| Fact | Where |
| --- | --- |
| WS handshake: `session_id` = `solara-session-id` cookie; `page_id` = `session_id` query param; `kernel_id` = path param (client-generated) | `starlette.py:301-347` |
| Unknown `kernel_id` → a **fresh, empty** `VirtualKernelContext` is created under that id. This is the "landed on a new instance" branch | `kernel_context.py:490-506` |
| Session hijack guard is in-process only: `context.session_id == session_id` | `kernel_context.py:496-501` |
| Reactive values live in `context.user_dicts[storage_key]`; `KernelStore.get()` lazy-inits **only if the key is absent** (guarded by per-(variable, kernel) `init_locks`, #1165) | `toestand.py:297-332`, `kernel_context.py:83-90` |
| With default mutation detection the stored object is a `StoreValue` wrapper (`MutateDetectorStore`), **not** the raw value | `toestand.py:546-564` |
| Auto-derived storage keys are `module:TypeName:N` with a **per-process creation counter** — not stable across instances or refactors. Only explicit `key=` is stable | `toestand.py:491-496` |
| All writes funnel through `KernelStore.set()`; no-op writes are already short-circuited by `equals` | `toestand.py:385-404` |
| Websocket messages are processed one at a time under `context.lock` — but reactive writes are **not** confined to that loop: tasks (`solara.lab.task`, `use_task`), threads, and asyncio callbacks mutate state at arbitrary times. Message boundaries are therefore not state-change boundaries | `server.py:156-192` |
| Client reconnect: on `connected`, sends `app-status`; `started: false` → `needsRefresh = true` → refresh dialog | `main-vuetify.js:164-193`, `solara.html.j2:76-104` |
| Dev hot-reload re-runs the app in the **same** kernel over **live** comms — its machinery does not transfer to a fresh-kernel remount, but proves remount-without-reload is supported | `app.py:491-504` |
| Clean close vs connection loss are already distinguished: `page_close` (beacon `POST /_solara/api/close/{kernel_id}`) vs `page_disconnect` + cull timer (`kernel.cull_timeout`, default 24h) | `kernel_context.py:219-359`, `starlette.py:769` |
| Redis precedent and core/enterprise split: `cache_type_map` keeps `memory` in core, `redis` in `solara_enterprise.cache.redis`, imported lazily | `cache.py:265-292` |
| Documented deadlock precedent: never do blocking I/O under a store lock | `docs/reactive-initialization-lock-deadlock.md` |

## 3. Design overview

```
Browser                LB          Instance B (fresh)                     Redis
  |  ws reconnect ----->|---> app_loop -> initialize_virtual_kernel
  |                     |       kernel_id unknown -> fetch state:
  |                     |         HGETALL solara:state:{kernel_id}  ----->|
  |                     |         verify HMAC(session_id); check schema tag
  |                     |         HINCRBY __generation__ (fence)    ----->|
  |                     |       create context, raw envelopes attached
  |  app-status ------->|     -> {started: false, canRecover: true, appVersion}
  |  run (current URL)->|     first render; persisted reactives lazy-init
  |                     |       from restored envelopes instead of defaults
  |  finished+widget_id<|     client swaps mount point -- NO refresh dialog
  |  ...interaction --->|     dirty-mark on set(); debounced flush   ----->|
```

Three independent pillars, one per section below:

- **A. Opt-in API + serialization** (`toestand.py`, `reactive.py`)
- **B. Server lifecycle: restore, write-behind, TTL, fencing, security** (`kernel_context.py`, `server.py`, settings, backend)
- **C. Client soft-remount, refresh dialog removal** (`main-vuetify.js`, templates, `app.py`)

Pillar C is also useful standalone: with a setting, apps whose state is fully derivable
(URL + DB) can enable soft-remount without Redis at all.

## 4. Pillar A — opt-in API and serialization

### 4.1 API

Extend `solara.reactive()` (one discoverable entry point; no parallel
`persistent_reactive` function). Persisted reactives need a **stable cross-process key**
— today's auto-derived storage keys are creation-order dependent
(`toestand.py:491-496`) and would silently mix up variables across deploys/instances.

**Key policy:** explicit `key=` is always allowed (and recommended for anything meant to
survive refactors). When omitted with `persist=True`, the key is **auto-derived from the
definition site** for the two statically unambiguous patterns, and everything else
raises a clear `ValueError` demanding `key=`:

1. **Class attribute** → `module:Owner.attr` via `Reactive.__set_name__`
   (`toestand.py:585` — currently only sets `_name`/`_owner` for repr; re-keying there is
   safe because `storage_key` is a plain attribute and `user_dicts` fills lazily, so
   nothing has read the key before class creation completes).
2. **Module-level single-name assignment** (`count = solara.reactive(0, persist=True)`,
   incl. annotated `n: int = ...`) → `module:varname`, derived with the `executing`
   library: resolve the exact `reactive(...)` `Call` node from the frame's bytecode
   offset (reusing `_find_outside_solara_frame()`'s skip-list, `toestand.py:414-450` —
   the same frame capture that mutation detection uses for its warning tracebacks,
   `toestand.py:463-468`, but invoked whenever `persist=True` and no key is given,
   independent of the `mutation_detection` setting), then require the parent to be a
   single-`Name` `Assign`/`AnnAssign` with no
   `FunctionDef`/`For`/`While`/comprehension/`If` ancestor.
3. **Refused (raise, demanding `key=`)**: definitions inside functions/factories/loops
   (same source name, many live instances — would silently clobber state), multi-target
   or tuple assignments, container/call-argument positions, attribute targets, and
   sourceless environments (frozen apps; notebooks work — solara already registers cell
   source in `linecache`, `autorouting.py:53-60`).

Derived keys are name-only (no line numbers), so reformatting doesn't change them.
Renaming or moving a variable does change the key → old state is discarded, consistent
with the version-tag-discard semantics (§5.2) — document this, and recommend explicit
keys for long-lived state. A small weakref registry (`derived_key → (source_location,
weakref)`) catches the residual collision (two module-level assignments deriving the
same key) and raises at persist-registration time; same-source re-registration is
allowed so hot reload keeps working.

Prior art: PR #517 derived `_varname` by string-splitting `inspect.stack()` frames (for
logging only) and stalled on a ~4s startup regression and fragile parsing; PR #515
changed auto-keys to caller-filename but stayed counter-based; issue #510 is the
counter-collision bug this class of problem causes. This design avoids #517's cost by
deriving **only when `persist=True`** (ordinary reactives: zero overhead) and avoids its
fragility by using AST-node resolution instead of line parsing. `executing` is already
a transitive dependency (via ipython); declare it explicitly in `pyproject.toml`.

```python
count = solara.reactive(0, persist=True)              # key auto-derived: "myapp.pages:count"
count = solara.reactive(0, persist=True, key="myapp.count")  # explicit, refactor-proof

filters = solara.reactive(
    Filters(),
    persist=solara.PersistConfig(
        key="myapp.filters",
        serializer="json",         # default; or "pickle" (gated, §4.2), or a registered custom codec
    ),
)
```

Pydantic models and dataclasses need no separate serializer (shipped post-v1-review): the
default json codec tags them **self-describingly** — the envelope records `module:qualname`
with the value, decode imports the class, gates on
`issubclass(BaseModel)`/`is_dataclass` (never instantiates an arbitrary class), and
validates. This is what makes `solara.reactive(None, persist=True)` (`Optional[Model]`)
work: with a None default no target class exists anywhere at definition time, so the class
must travel with the value. Trade-off, documented: renaming a persisted model class breaks
old envelopes (bail-out; schema-tag bump = clean reset). Pydantic round-trip semantics
match `model_validate(model_dump())` exactly.

`PersistConfig` is deliberately two fields in v1. Cut after review (maintainer): per-
variable `ttl` (needs emulation the hash can't do natively; kernel-scoped TTL is the
right granularity), per-variable `backend` (one process-wide backend), and per-variable
`version`/`migrate` (redundant with the global state-version tag for v1, semantically
confusing next to it, and `migrate` would run arbitrary author code under `init_locks`
— the documented deadlock surface). Value-shape evolution in v1 = bump the global tag =
clean state reset.

**The refusal error message is a specified deliverable, not an afterthought** (DX
review — the naive fix for the factory refusal is a `key="query"` constant, which makes
*every user share one Redis field*: cross-user state disclosure on restore). The
message must, at the quality bar of the existing mutation-detection message
(`toestand.py:509-517`): name the definition site (file:lineno + code line), explain
*why* (a factory/function creates many instances sharing one source name), and show the
correct fix with a per-instance discriminator:

```
ValueError: persist=True requires an explicit key= here: a reactive created inside a
function/factory (myapp/state.py:42: `query = solara.reactive("", persist=True)`)
produces one instance per call, and they cannot share a key. Give each instance a
unique key, e.g.:  solara.reactive("", persist=True, key=f"user:{user_id}:query")
NEVER use a constant key here — instances would overwrite each other's state.
```

**The store pattern gets a first-class recipe** (DX review: Solara's own state-
management docs teach reactives created in `__init__`, which the derivation refuses —
the docs' idiomatic pattern must not be a dead end). The recipe: store constructors
take an id and key their reactives `f"{prefix}:{instance_id}:{attr}"`; evaluate a small
helper (e.g. `PersistConfig(key_prefix=...)` on a store base class) during
implementation.

Auto-derived keys are logged once at INFO (`derived persistence key
"myapp.pages:count"`), so a rename-induced state reset is greppable. Docs position
explicit `key=` as the norm for long-lived state and bare `persist=True` as prototype
convenience — the derived key embeds the module path and does not survive file
moves/renames.

- `persist=True` is sugar for `PersistConfig(key=<explicit or derived key>)`.
- Persisted keys are namespaced (e.g. `reactive:` prefix) — `user_dicts` is shared with
  `solara.scope` (`patch.py:246`).
- A process-global registry maps `storage_key -> PersistConfig` so restore and flush know
  the persisted set.
- `Ref(...)` fields need nothing: field writes flow through the root reactive's `set()`.
- **Decided:** no `solara.lab` gating — `persist=`/`key=` land directly on
  `solara.reactive()` as stable API, and the lifecycle additions (§5.5b) in the core
  `solara.*` namespace.

### 4.2 Serialization: JSON-first, signed envelopes

Prior art is unambiguous (Django moved sessions to JSON after pickle-cookie RCEs; Celery
refuses pickle by default; Reflex's worst production bugs are all arbitrary-objects-
reaching-pickle):

- **Default serializer: strict JSON-ish codec** — primitives, list/dict, and (DX
  review: these come straight out of real widget/filter state and must ship in the
  default codec, not be left to custom hooks) **datetime/date/time, enum.Enum, numpy
  scalars (`np.int64`/`np.float64`), UUID, Decimal, and set** — plus dataclass/pydantic
  hooks with a worked example of a dataclass containing an Enum + date field. Document
  a type-support matrix (type → supported/coerced/how) and the tuple→list round-trip
  caveat. This covers the realistic opt-in set (filters, selections, form fields, page
  state); enums and numpy scalars are where authors hit the wall first without
  coercion.
- **Pickle only as explicit per-variable opt-in** (`serializer="pickle"`), documented:
  fast and general, but version-skew fragile and RCE-if-Redis-compromised.
- **Every stored value is an HMAC-signed envelope**, verified **before** any
  deserialization. Cheap (~µs), converts "Redis write access ⇒ RCE" into "Redis write
  access AND app secret ⇒ RCE", and gives tamper-integrity to the JSON path for free.
  Full specification (security review):
  - **HMAC-SHA-256, full 32-byte digest, compared with `hmac.compare_digest`.**
  - **Signing input = length-prefixed canonical encoding** of
    `(key_id, kernel_id, field_name, codec, payload)` — length-prefixing each component
    prevents ambiguous-concatenation attacks. **The generation is NOT part of the
    signature** (see §5.5 — a takeover bumps the generation before the restore read, so
    generation-bound envelopes could never verify; fencing arbitrates *writes*, HMAC
    proves *integrity*, and the two must not share inputs).
  - **Dedicated secret: `SOLARA_STATE_SECRET_KEYS`** — an ordered list; the envelope's
    `key_id` selects the verify key; verification accepts any listed key, writes use the
    first. Two-phase rotation (add-new-verify-only → promote → drop-old) without a
    fleet-wide bail-out. Deliberately NOT the OAuth/session cookie secret
    (`SOLARA_SESSION_SECRET_KEY`): one secret must not span cookie forgery, state
    tamper, and pickle RCE. Enforced non-default/non-empty at startup when persistence
    is enabled (note: today's non-default enforcement only fires under OAuth,
    `settings.py:233-238` — this adds a new check).
  - **Pickle requires a deployer-side gate**: `serializer="pickle"` raises unless
    `SOLARA_STATE_ALLOW_PICKLE=true` is set in the environment — application/library
    code must not be able to opt a deployment into a pickle-deserialize path silently.
    Startup refuses pickle+default-secret outright.

### 4.3 Failure semantics (decided: all-or-nothing restore)

Two categories, deliberately treated differently:

- **Expected discard — global `__version__` tag mismatch** (a live redeploy): not a
  failure. The whole hash is discarded, the kernel starts fresh, the client
  soft-remounts into fresh state. Live redeploys "just work", with a state reset. Log
  INFO + metric.
- **Unexpected failure — any envelope fails HMAC verification or codec decode** →
  **bail out entirely**: discard *all* restored values, flag the context as
  recovery-failed, and tell the client to hard-refresh (§6.1, `canRecover: false`). Log
  ERROR with the failing key and cause (tamper vs skew vs bug mean different things) +
  metric. Rationale: a partially restored state — some variables restored, others
  silently at defaults — is a state no app author ever designed for or tested; a
  visible "we lost, please refresh" is more honest than a silently inconsistent app.
  Two hardenings from review:
  - **The poisoned hash is deleted (or renamed to a dead-letter key for forensics) at
    bail-out** — symmetric with the serialize-failure path. Without this, the same
    kernel id (programmatic reconnect, bookmarked `?kernelid=` link) re-reads the same
    poisoned envelope on every fresh instance and loops in permanent bail-out until
    TTL (dist-sys review).
  - **Bail-out rate valve** (SRE review): if more than X% of restores in a window bail
    out (a bad deploy — e.g. a forgotten version bump — hits *every* reconnecting
    session at once), stop showing the dialog and degrade to today's silent
    fresh-start. A fleet-wide dialog storm plus synchronized refresh/DB herd is worse
    than the disease; degraded mode must never be worse than no feature.
- **Serialize failure at write**: the strict JSON codec fails deterministically on the
  *first* write, so authors hit this immediately in dev — fail loudly there. In
  production (rare — a code path that puts an unexpected type in an opted-in reactive):
  log ERROR, **delete the kernel's hash and stop persisting for this kernel** — no
  false confidence; a reconnect then restores nothing (fresh state) rather than a
  stale-or-partial snapshot.
- **Size guard**: warn at ~1 MB serialized per variable (Reflex's number), configurable.
  Large dataframes belong in a DB/object store; persist the reference.

### 4.4 Dirty-tracking and restore mechanics

- **Dirty-mark via `subscribe_change`, not by editing `set()`** (maintainer review —
  strictly less invasive). `KernelStore.set()` already calls `fire()` *after* the
  `equals` short-circuit (`toestand.py:392,404`), so registering
  `reactive.subscribe_change(mark_dirty)` at persist-registration time gives identical
  coverage — all sources (message handlers, tasks, threads), no no-ops — with **zero
  edits to the deadlock-sensitive `set()` method** (#1165 landed in this file 28
  commits ago). Bonus: `MutateDetectorStore.subscribe_change` hands the listener the
  already-**unwrapped** value, sidestepping the `StoreValue` wrapper on the write side.
  The listener only adds the key to a per-context dirty set and schedules the debounced
  flush (§5.3). **No I/O in the listener, ever** (deadlock precedent). Caveat to
  document (dist-sys review): with `mutation_detection` off (the production default),
  in-place mutation of a persisted value never fires `subscribe_change` (the `equals`
  check compares the mutated object to itself) — so in-place mutation escalates from
  "missed rerender" to "state silently not persisted"; the existing "don't mutate
  reactives in place" rule becomes load-bearing and the docs must say so.
- **The registry maps `storage_key → (PersistConfig, weakref-to-public-Reactive)`**,
  not just config (maintainer review): flush must `peek()` the *public* store
  (`MutateDetectorStore.peek()` unwraps; `KernelStore.peek()`/`user_dicts` return the
  `StoreValue` wrapper).
- **Restore = eager fetch, lazy install.** The connect path fetches the raw hash once
  (§5.1) and attaches the raw envelopes to the context. Actual deserialization happens
  per variable at the existing lazy-init seam in `KernelStore.get()`
  (`toestand.py:320-332`, under the per-(variable, kernel) `init_locks`): if a restored
  envelope exists for this key, verify + deserialize + use it in place of
  `initial_value()`; on any failure → bail-out (§4.3). This:
  - handles the `MutateDetectorStore`/`StoreValue` wrapping **explicitly** — the
    maintainer review corrected an earlier claim that wrapping "applies naturally":
    with mutation detection on, `initial_value()` returns an already-wrapped
    `StoreValue(private=…)` built in `mutation_detection_storage()`, so restore must
    deserialize the raw value and **reconstruct the wrapper itself** (two code paths:
    wrapped when mutation detection is on — dev default — raw when off — prod
    default). The serializer always operates on the unwrapped value. Raw `user_dicts`
    population would corrupt mutation detection. Real, test-covered work, not free;
  - constrains the codec: it runs under `init_locks`, so **no I/O, no widget
    construction, no logging that touches reactives** (same contract as
    `initial_value`; #1165 crossed *different* locks via a logging handler);
  - makes ordering with `on_kernel_start` callbacks a non-issue (whoever reads first
    gets the restored value);
  - names the failing variable and cause precisely in the bail-out ERROR;
  - installs without firing listeners and without marking dirty.
- **Flush snapshots under the lock, serializes outside** (dist-sys review): `peek()`
  returns the live object reference, and a task mutating it mid-serialization gives a
  torn snapshot or `RuntimeError: dict changed size during iteration`. The flush worker
  takes a cheap `deepcopy` (or codec-encode of immutables) under the store lock, then
  serializes + HMACs the copy off-lock. Reading at flush time still coalesces bursts
  for free.
- **Keys stay dirty until the write is ACKed** (dist-sys review): draining the dirty
  set before the Redis write means a rejection, an error, or the circuit breaker
  opening mid-flush silently drops those keys until some unrelated future write.
  Failed/rejected/breaker-blocked flushes re-mark their keys dirty.

## 5. Pillar B — server lifecycle

### 5.1 Restore hook

In `initialize_virtual_kernel`, **new-context branch only** (`kernel_context.py:503`):
run the backend `takeover` with a hard timeout (~300 ms) and attach the returned raw
envelopes to the new context. On any error or timeout: log WARNING, continue with fresh
state. Never block beyond the deadline; never crash.

**Verify-then-bump, atomically, and never write on a miss** (security review — an
earlier draft had the bump before verification, which let an unauthenticated client
create unbounded Redis keys via random `?kernelid=` values and bump generations on
*other users'* kernels, a takeover-DoS that forces the victim's instance into fence
churn). The takeover Lua script, as one atomic unit:

1. If the key **does not exist**: write **nothing**, return empty. The hash is created
   only by the first legitimate *flush* (which writes `__session_id__`, `__version__`,
   and `__generation__` together with the first fields — this also answers "who writes
   the identity fields", previously unspecified).
2. If the key exists but `__session_id__` is missing or ≠ the caller's session-HMAC:
   **reject, no write** (missing identity is a hard reject, not "nothing to check").
3. Only on identity match: check `__version__` (mismatch → the script deletes the hash
   and returns "fresh": clean redeploy reset); else `HINCRBY __generation__`, `HGETALL`,
   return.

**Fresh-start must claim-or-delete** (dist-sys review — zombie resurrection): every
path that decides "continue with fresh state" while a hash exists (restore timeout,
version discard, bail-out §4.3) must not leave the old hash readable, or a *later*
failover would silently roll the user back to the pre-timeout snapshot after they've
diverged. Timeout → claim ownership on the next successful flush (which is fenced and
re-stamps identity at the generation it bumps); version/bail-out → the hash is deleted
in the script/bail-out path itself.

Additionally (security review): **validate `kernel_id` against a strict UUID pattern at
the websocket entry** (`starlette.py:324` currently accepts any string, which becomes a
Redis key and a cluster hash-tag — namespace injection and `SCAN`-pattern pollution),
and apply the same validation on the existing close route.

**The reuse branch also verifies ownership** (`kernel_context.py:493-502`): a fast
double reconnect can land back on an instance whose old kernel context is still alive in
memory (orphan cull not yet fired) *after* another instance took over in between.
Resuming that context blindly would roll the user back to pre-takeover state and, worse,
the instance's next flush would be fence-rejected while it holds a live socket. So on
reconnect-to-existing-context, compare the remembered generation with Redis:

- **Match** → pure hot reconnect, today's fast path, no state touched (the overwhelmingly
  common case, including single-instance deployments — with no takeover the generation
  never moves). This check-then-serve has a narrow TOCTOU window (another instance
  completing takeover between the peek and the resume, dist-sys review) — it is closed
  not by locking the connect path but by the write path: a later fenced-write rejection
  puts this instance through the §5.5 rejection protocol, whose single re-takeover
  re-establishes a correct order.
- **Mismatch** → superseded while disconnected: the in-memory state is stale relative to
  Redis (the user's most recent work happened elsewhere and was flushed there). Close the
  old context (`close_reason="superseded"`), create a fresh one, run the normal atomic
  takeover + restore, and let the client soft-remount. This preserves the user's latest
  work at the cost of resetting non-persisted state — the correct trade, consistent with
  the feature's premise. (Optimization, not v1: skip the remount when Redis state is
  byte-identical to the instance's own last flush.)

Async mode (`threaded=False`) runs `app_loop` on the shared event loop, so the fetch must
go through a worker thread (`run_in_executor`); a sync `redis` client on a worker thread
is sufficient everywhere (mirrors `solara_enterprise.cache.redis`).

Also: take a small lock around the check-and-create in `initialize_virtual_kernel`
(`kernel_context.py:493-506`) — the existing race is benign today but shouldn't be once
I/O and generation bumps live there.

### 5.2 Redis layout

One hash per kernel — one Redis key, but **not** one serialized blob:

```
Key: solara:state:{kernel_id}      TTL refreshed on every write and on connect
Fields:
  reactive:{persist_key} -> signed envelope (per opted-in reactive)
  __session_id__         -> HMAC(session_id, SOLARA_SESSION_SECRET_KEY)
  __version__            -> app/schema tag (mismatch => discard, log, fresh start)
  __generation__         -> int, fencing token
```

Rationale vs the alternatives (single-blob string key; one string key per variable):

- **Atomicity where it matters, free.** Single Redis commands are atomic: one multi-field
  `HSET` per flush writes the whole dirty batch atomically, and `HGETALL` reads
  atomically — a restore can never observe a torn flush. That is batch-level snapshot
  consistency without MULTI/WATCH. A blob's whole-state consistency adds nothing given
  our last-writer-wins-per-flush semantics; nesting *within* a variable (one dataclass =
  one field) remains the answer for cross-variable invariants (§5.3).
- **TTL is per key, not per field** (hash-field `HEXPIRE` needs Redis ≥7.4, which managed
  services barely offer). Kernel-scoped lifetime → one TTL on one key is exactly right;
  per-variable string keys would need N `EXPIRE`s per flush and could expire piecemeal.
  Per-variable TTL overrides are therefore emulated (timestamp in the envelope, checked
  at restore) rather than delegated to Redis.
- **No write amplification.** Dirty-only field writes: a counter update next to a 500 KB
  persisted value costs bytes, not the 500 KB a blob rewrite would (serialize + HMAC +
  network + Redis's single command thread on a big value). Reflex's dirty-substate
  design is this same lesson.
- **Per-variable diagnosability**: restore is all-or-nothing (§4.3), but per-variable
  envelopes mean the ERROR log names exactly *which* variable failed and why — with a
  blob you'd know only "something is corrupt". Dirty-only writes and the size warning
  also need per-variable granularity.
- **Fencing and cluster locality**: `__generation__` lives in the same hash, so the Lua
  fenced write touches one key, and a hash is always one cluster slot (per-variable keys
  would need `{kernel_id}` hash tags).
- **Ops legibility**: `DEL` wipes a session atomically, `SCAN` counts sessions,
  `MEMORY USAGE` sizes one, and `HGETALL` in redis-cli shows named fields.
- **RedisJSON rejected**: it is a module unavailable on ElastiCache/Memorystore, and
  JSONPath partial updates are incompatible with HMAC-signed opaque envelopes (any
  change requires re-signing the whole value anyway).
- **Caveat**: `HGETALL` is O(total size); with the ~1 MB-per-variable warn threshold
  (§4.3) and tens of variables this is single-digit ms. The blob-only advantage — one
  HMAC covering the whole set including *absence* of fields — is addressed by context
  binding (below); field deletion by an attacker degrades to default-value fallback,
  equivalent to state loss.

**HMAC context binding:** the signature input includes `kernel_id` and the field name
(§4.2 — length-prefixed canonical encoding) — so an envelope cannot be replayed into a
different kernel or a different variable by an attacker with Redis write access.
**Deliberately NOT the generation**: two reviews independently confirmed that
generation-bound envelopes can never verify after a takeover bumps the counter (every
failover would bail out — the feature would be dead on arrival), and a
generation-embedded-in-envelope variant is self-referential and adds zero replay
protection. Fencing arbitrates writes; HMAC proves integrity; they share no inputs.
Replaying an *older* value for the same field/kernel remains possible and is accepted
for v1 (within the Redis-write-access threat model, where the bail-out path bounds
impact).

### 5.3 Write path

State changes do not align with websocket message boundaries: re-renders and reactive
writes are routinely triggered from tasks (`solara.lab.task` / `use_task`, plain threads,
asyncio callbacks) that complete long after the triggering message was processed — or
with no triggering message at all (timers, pollers). The write path therefore treats all
mutation sources uniformly:

- **One debounced write-behind worker per kernel is the primary mechanism.** The
  `subscribe_change` dirty-mark (§4.4) schedules a coalescing flush (~200-500 ms after
  the first mark) regardless of where the write came from. The worker snapshots dirty
  values (deepcopy under lock, §4.4), serializes + HMACs off the hot path, and calls
  the backend's fenced `flush` — the only write path (§5.5). Every backend write
  carries a hard socket/op timeout (an earlier draft had a timeout only on restore);
  keys stay dirty until ACK (§4.4). The worker enters the kernel context
  (`with context:`) before touching stores — a context-less thread would resolve
  reactives to the global scope and serialize defaults (dist-sys review).
- The post-`process_kernel_messages` point (`server.py:184`) is **not** a sufficient
  flush boundary — it misses every task/thread-driven write. At most it serves as an
  optional flush-now hint so direct interaction effects reach Redis with less latency
  than the debounce window; v1 can skip it entirely (one code path, and the debounce
  window already bounds staleness).
- **No cross-variable atomicity.** Flushes are per-variable last-value-wins and can land
  between two related writes made by a task. Documented guideline: state with invariants
  spanning values belongs in a single reactive (one dataclass), which serializes
  atomically as one hash field.
- **Best-effort flush on graceful teardown — with honest reach and hard bounds.** Two
  reviews corrected an earlier "deploys and scale-downs restore exactly what the user
  saw" claim:
  - *Reach* (dist-sys): the per-kernel disconnect flush rides on
    `ws.receive()` returning/raising (`server.py:161,194`). OOMKill, SIGKILL, spot
    reclamation, and LB blackholes/half-open TCP produce **no observed disconnect** —
    those scenarios get no final flush; their loss window is the debounce interval at
    best and unbounded for background writes after the silent drop. The final flush
    reliably covers: clean tab-close, client-initiated close, observed TCP resets, and
    lifespan shutdown. Say this plainly in docs.
  - *SIGTERM* (SRE): `on_shutdown()` (`starlette.py:627`) only runs when uvicorn's
    lifespan teardown runs, and uvicorn waits for connections **indefinitely** by
    default — a lingering websocket stalls the drain until Kubernetes SIGKILLs and
    nothing flushes. Ship with `timeout_graceful_shutdown` set (and documented against
    `terminationGracePeriodSeconds`), and make the shutdown flush **one bounded,
    batched, parallel pass** over all contexts (global deadline of a few seconds, one
    pipelined write per batch) — not N serial 300 ms-timeout calls, which under a
    correlated Redis brownout is 500 × 0.3 s = 150 s ≫ any grace window.
  - *Locking* (dist-sys): the teardown flush must not run Redis I/O while holding
    `context.lock` (`close()` holds it; the message loop and cull take it) — snapshot
    under the lock, write outside it, with the bounded timeout. This is the documented
    deadlock pattern.
- **Circuit breaker — specified, not gestured** (SRE review): consecutive-failure
  threshold N (default ~3), open window (default ~30 s), half-open single-probe policy;
  all three in settings; per-process. **It gates restores as well as writes** — with
  the breaker open, connects skip the takeover read instantly instead of each paying
  the 300 ms deadline during a brownout (which would tax the connect path precisely
  during a deploy herd). Every state transition logs one WARNING line and increments a
  counter (§7a); breaker state is exposed on `/resourcez`. Flapping risk (slow-not-down
  Redis) is bounded because writes are off-thread — flapping costs consistency of the
  *recovery* copy, never interaction latency; keys stay dirty until ACK so recovery
  after re-close is complete.
- Semantics documented honestly: **at-most-once / best-effort**. "On failover you get
  your state back as of at most the debounce window before the disconnect — when the
  disconnect is observed or the shutdown is graceful; a hard kill or silent network
  drop may lose more."

### 5.4 Lifetime, TTL, culling

- TTL = `kernel.cull_timeout` by default (24h), refreshed on write and on connect.
- **`DEL` is gated on `close_reason` and fenced** — the blocker both the dist-sys and
  SRE reviews independently found: `close()` (`kernel_context.py:157`) is the single
  convergence point, but it is reached by the tab-close beacon, the cull timer, the
  superseded path, **and `on_shutdown()` (`starlette.py:627`), which closes every
  context on SIGTERM**. An unconditional `DEL` there would wipe every session's state
  on every rolling deploy (the feature's headline scenario), delete nothing-to-restore
  after the orphan cull, and — on the superseded path — delete the hash the *new*
  instance is actively using. Rules:
  - `close_reason == "page-close"` (user genuinely closed the tab) → fenced `DEL`
    (delete iff `__generation__` is still ours — never delete a hash another instance
    now owns);
  - `"cull"`, `"superseded"`, `"server-shutdown"` → **flush-and-leave-for-TTL**; no
    delete. TTL reclaims abandoned state.
- **New knob: shortened orphan cull** — gated on a **shared** backend (SRE review). With
  state in a networked backend there is no reason to keep an orphaned (disconnected)
  kernel alive for 24h: cull after `SOLARA_STATE_ORPHAN_CULL_TIMEOUT` (default ~5m);
  Redis TTL stays long so later reconnects still restore. **Honesty correction** (an
  earlier draft claimed the hot-reconnect window was "untouched" — false): this knob is
  exactly what shortens the same-instance live-kernel window from 24h to ~5m, and a
  slow reconnect (>5m, e.g. flaky mobile) then gets only persisted state back where
  today it gets everything. That is the intended trade for multi-instance; for
  `memory`-backend/single-instance setups the shortened cull must NOT apply (state and
  kernel die together — shortening only loses state). Document the trade explicitly.

### 5.5 Split-brain fencing

After the LB moves the socket, instance A's kernel may live on (background tasks still
writing) while instance B restores and takes over. Without fencing this is
last-writer-wins — survivable, but the fix is cheap, so v1 includes it:

- On restore, B's takeover script (verify → bump → read, §5.1) leaves B holding the
  current `__generation__`.
- **The fenced Lua script is the ONLY write path** (dist-sys review — an earlier draft
  offered a plain pipeline "or" the fenced write; an unfenced `HSET` defeats the entire
  fence and can resurrect a deleted hash). The script: check `__generation__` matches →
  `HSET` dirty fields (+ identity fields on first write) + `EXPIRE`, all inside the
  script — else return REJECTED, writing nothing.
- **Rejection protocol — bounded, never an unbounded reclaim loop.** An earlier
  revision reclaimed ownership whenever the instance saw a CONNECTED page; the
  dist-sys review showed that's a livelock: `page_status` reflects *observed*
  disconnects only, so under half-open TCP (the exact failure this feature targets) or
  two tabs on two instances, **multiple instances believe they hold a live socket** and
  duel with `HINCRBY` + full re-flush forever. Revised rules:
  - no CONNECTED page → orphan, legitimately superseded → stop the flush worker,
    early-cull (`close_reason="superseded"`), **flush-and-leave** (§5.4), no reclaim;
  - CONNECTED page(s) → **at most ONE re-takeover per connection epoch** (an epoch
    starts when a websocket for this kernel connects to this instance): fenced
    verify+bump, keep in-memory state (do not apply the read), mark-all-dirty,
    re-flush once. If rejected **again** within the same epoch → **concede**: stop
    persisting, keep serving the live session from memory, log
    `superseded-while-connected` (WARNING + metric — this is the signature of broken
    LB stickiness, cross-instance multi-tab, or an attack; it should be loud). A new
    epoch (genuine client reconnect through `initialize_virtual_kernel`) naturally
    re-takes ownership.
  - Convergence: a half-open "believer" re-takes at most once and concedes; the true
    socket holder's next epoch (or its single re-takeover) wins. Two *genuinely*
    connected tabs on two instances (no stickiness) end with one persisting and one
    conceded-but-serving — degraded but stable, honestly logged; docs state that
    same-kernel multi-tab requires stickiness for full persistence.
  - The concede path also bounds the reclaim write-amplification (full-state re-flush
    happens at most once per epoch, not per debounce window).
- Takeover must itself be one atomic Lua unit (verify → `HINCRBY` → `HGETALL`, §5.1):
  every old-instance write is then cleanly on one side — before the bump → included in
  the restore read; after → rejected. Two separate commands would leave a window where
  a write is fenced for the future but missed by the restore (a lost update).

### 5.5b Cooperative shutdown and ownership API

Supersession is deliberately **not** a new lifecycle state for app code — it is a new
*reason* for the existing close. The fence-rejection → early-cull path ends in
`context.close()`, which sets `closed_event` (`kernel_context.py:102`, already polled by
tasks, `tasks.py:328`), cancels tasks, unmounts components (setting `use_thread` cancel
events, `hooks/misc.py:68,136`), and runs `on_kernel_start` cleanups. Well-behaved
background code therefore stops with no new API. On top of that:

- **v1 — `solara.kernel_closed_event() -> threading.Event`**: public accessor for
  user-managed threads (today this requires reaching into the server-internal
  `kernel_context.get_current_context().closed_event`). Captured inside the kernel
  context at thread-spawn time; supports both `wait()` and loop-guard polling. Chosen
  over `should_stop()` (nice loop ergonomics, but hides the Event and is vague) to
  introduce zero new vocabulary; a bool sugar can come later.
- **v1 — `context.close_reason`**: `"page-close" | "cull" | "superseded" |
  "server-shutdown"`, logged and exported as a metric — repeated `superseded` closes
  indicate LB misconfiguration (missing/broken stickiness causing takeover churn).
- **v1 — `solara.state_generation() -> Optional[int]`** (promoted from v2 on DX-review
  pressure: without a fencing token, no wizard/checkout app can make its external side
  effects failover-safe, and §6.5's own headline example is undeliverable). Nearly free
  — it returns the instance's remembered generation, no Redis round trip. Apps pass it
  into their own external writes (DB rows, idempotency keys) as a true fencing epoch.
- **v2 — `solara.owns_state() -> bool`**, the active probe (one backend round trip
  comparing the remembered generation; returns `True` when persistence is disabled).
  Advisory only — check-then-act still races; the generation token is the real
  guarantee, which is why it ships first.

### 5.6 Settings

Follow the existing `BaseSettings` pattern (`settings.py:110-118`):

```python
class State(BaseSettings):
    backend: str = ""                  # "" = disabled; name in state_backend_map ("redis", "memory", ...)
    url: str = ""                      # backend DSN, e.g. "redis://localhost:6379/0"
    secret_keys: List[str] = []        # HMAC keys; verify-any, sign-first (rotation §4.2). REQUIRED when enabled
    allow_pickle: bool = False         # deployer gate; serializer="pickle" raises without it (§4.2)
    ttl: Optional[str] = None          # default: kernel.cull_timeout
    orphan_cull_timeout: str = "5m"    # applies only with a shared backend (§5.4)
    prefix: str = "solara:state:"      # key prefix / table name, backend-interpreted
    flush_debounce: str = "300ms"
    connect_timeout: float = 0.3       # hard cap on takeover/flush blocking
    breaker_failures: int = 3          # circuit breaker: consecutive failures to open
    breaker_window: str = "30s"        # open duration before a half-open probe
    schema_tag: str = ""               # state-schema tag ("" -> derived); mismatch => clean state reset (§6.1)
    auto_remount: Optional[bool] = None  # None: on iff backend set; can force on/off
    bailout_storm_threshold: float = 0.5  # bail-out rate valve (§4.3)

    class Config:
        env_prefix = "solara_state_"
```

Startup validation when `backend` is set: `secret_keys` non-empty and non-default;
pickle+missing-gate refused; recommend (and log if not) `SOLARA_SESSION_HTTP_ONLY=true`
— verified: the JS never reads the session cookie (`main-vuetify.js:94` defines the
name and never uses it), so `http_only=True` is free hardening; today's default is
`False` (`settings.py:137`). Also stop co-logging `session_id` with `kernel_id` at INFO
(`starlette.py:329`) — with Redis restore those two strings together are a complete
state-theft credential; hash or redact.

The `fence` on/off knob was removed (security review): with verification inside the
takeover script and the fenced script as the only write path, unfenced operation is not
a meaningful mode.

### 5.7 Backend abstraction and code placement

Redis is the only production backend in **v1**, but the interface is deliberately not
Redis-shaped. A MutableMapping-style protocol (the `cache/base.py` shape) cannot express
fenced writes, so the contract is exactly the four verbs the feature needs, with the
atomicity requirements in the contract rather than in Redis features:

```python
class StateBackend(Protocol):
    def takeover(self, kernel_id, session_hmac) -> tuple[int, dict[str, bytes]]:
        """Atomically claim ownership and read all envelopes: bump-then-read as one
        unit. Returns (new_generation, fields). Raises/None on identity mismatch."""
    def flush(self, kernel_id, generation, fields: dict[str, bytes], ttl) -> bool:
        """Atomically write the batch iff generation still matches (fenced).
        Returns False when rejected."""
    def peek_generation(self, kernel_id) -> Optional[int]:
        """Cheap ownership check (reuse branch, owns_state() probe)."""
    def delete(self, kernel_id) -> None:
        """Atomic wipe on clean close."""
```

Everything in §5.2/§5.5 (hash layout, Lua scripts) is then *how the Redis backend
satisfies this contract*, not the design itself. Implementations:

- **redis** (v1, production): Lua for `takeover`/`flush`, hash-per-kernel, key TTL. Note
  this transparently covers Valkey/KeyDB/Dragonfly (Redis-protocol compatible via
  redis-py) — worth documenting, since much managed "Redis" is Valkey post-license-fork.
- **memory** (v1, core): dict + lock; for tests and local development. **Fidelity is
  pinned** (dist-sys review — otherwise the marquee single-process failover test can be
  green while Redis is red): the memory backend stores the same
  codec-encoded, HMAC-signed envelope **bytes** (never live objects) and implements the
  same takeover/flush/fence contract, so serialization bugs and fencing logic are
  exercised in dev. Documented as structurally unable to cover: network
  latency/timeout paths, torn-connection behavior, and eviction — those need the
  two-process Redis test (§9).
- **postgresql** (future, deliberately enabled by this contract): a single table +
  transactions gives all four verbs natively; TTL via timestamp column + periodic sweep.
  "We already run Postgres and don't want another stateful service" is the most common
  ops objection to Redis — with this contract that backend is a ~100-line contribution,
  not a redesign.

Placement (**decided**): everything lives in **core solara-server** — hooks, registry,
opt-in API, settings, the `StateBackend` protocol, the memory backend, *and* the Redis
backend (`solara/server/state/redis.py` or similar), with `redis` imported lazily and
required only when `backend=redis` is configured (optionally a `solara[redis]` extra).
No solara-enterprise involvement — this is simply a new use of Redis, like caching.
The `state_backend_map` name→class registry still follows the `cache_type_map` shape
(`cache.py:265-292`) so third-party backends can register without touching core.

## 6. Pillar C — client soft-remount (no refresh dialog)

### 6.1 Protocol — and the two-versions distinction

The SRE review caught a contradiction between §4.3 ("a deploy soft-remounts gracefully")
and an earlier draft of this section ("a deploy shows the dialog"). Root cause: **two
different versions were conflated under one name.** They are now separate concepts with
separate triggers:

- **State-schema tag** (`schema_tag`, server-side, stored as `__version__` in the
  hash): "can old envelopes be decoded by this code?" Mismatch → the takeover script
  discards the hash → fresh state → **soft-remount**. A live redeploy that changes the
  persisted-value shape "just works", with a clean state reset. No dialog.
- **Client bundle version** (`clientVersion`, an opaque hash of the served JS/template
  assets — opaque, not a semver string, per the security review): "is the JS running in
  the browser still compatible with this server?" Mismatch → **hard-refresh dialog is
  genuinely correct** (the browser needs new assets; a soft-remount on stale JS is
  wrong).

`app-status` reply (`app.py:481-489`) gains two fields:

```python
{"method": "app-status", "started": bool,
 "canRecover": <persistence enabled or auto_remount forced, and not recovery-failed>,
 "clientVersion": <opaque asset hash>}
```

Client decision on reconnect:

- `started: true` → today's `fetchAll()` (same-instance hot reconnect — unchanged).
- `started: false && canRecover && clientVersion == own` → **soft-remount** (including
  after a schema-tag reset — the client can't tell and doesn't need to).
- otherwise → today's `needsRefresh` dialog: recovery disabled, the client bundle
  changed, or **restore bailed out** (§4.3, `canRecover: false` on a recovery-failed
  context — "we lost", visibly; subject to the bail-out storm valve).

So the deploy runbook is decidable: schema-only deploys → remounts (expected);
bundle-changing deploys → dialogs (expected, once); dialogs *without* a bundle change →
incident (check bail-out rate, secret uniformity, §7a).

`canRecover` is true when a state backend is configured **or** `auto_remount` is forced
on (for apps whose state is fully URL/DB-derived and needs no backend at all).

**No CDN release needed.** The bundled `widgetManager.appStatus()` hardcodes its reply
shape (`packages/solara-widget-manager/src/manager.ts:127`, drops extra fields), so the
client re-implements the ~15-line control-comm probe inline in `main-vuetify.js` and
reads `canRecover`/`appVersion` directly. All changes ship in the pip package
(`main-vuetify.js`, loader templates, `solara.html.j2`, `app.py`) — a normal patch
release; the version-pinned `@widgetti/solara-vuetify-app` bundles are untouched.

### 6.2 Remount sequence (replaces `main-vuetify.js:185-187`)

1. Guard `remountInProgress`; popouts (`?modelid`) keep current behavior (they attach to
   a specific model that no longer exists; dialog or auto-close).
2. Show a light "Restoring session…" indicator (reuse the top progress bar / small
   overlay — not the full loader; keep the stale DOM visible until swap).
3. Tear down: `widgetManager.clear_state()`/`dispose()` (closes dead comms, disposes
   models); delete the module-level `widgetPromises`/`widgetResolveFns[mountId]` caches
   (`main-vuetify.js:46-62` — settled promises would otherwise make re-mount a no-op).
4. Bump a new `remountKey` bound as `:key` on `<jupyter-widget-mount-point>` (loader
   templates) so Vue destroys and recreates the mount point. Do **not** toggle `loading`
   — that entangles the SSG/pre-render watcher (`solara.html.j2:341-367`).
5. New `WidgetManager` on the same reconnected kernel; recompute the path **now** from
   `window.location` (pushState routing means the boot-time `path` variable is stale);
   `run(appName, {path, dark, themes})`.
6. Server restores state before/at first render (Pillars A+B), replies new root
   `widget_id`; `solaraMount()` swaps it in. Clear the guard and indicator.

Edge cases handled: flapping reconnects (guard + re-check connection before final swap;
last completed attempt wins), fast double reconnect landing back on the original
instance (server discards its stale context on generation mismatch, §5.1 — the client
just sees another `started: false` + `canRecover` and soft-remounts; no client-side
special case needed), multiple tabs sharing one kernel id (each re-runs `run`; restore
is idempotent — fetch-once per fresh context; each tab gets its own container), SSG
pages (dedicated `remountKey`), in-flight input during the outage is lost — documented,
with LiveView-style client input re-send as a v2 candidate.

### 6.3 UX

During the outage: the existing "Server disconnected" overlay, unchanged. On reconnect:
brief "Restoring session…" progress, then the app is back — same URL, opted-in state
intact, derived state recomputed. No dialog, no reload. (Also fix in passing: the dead
`stateReset()`/`wsWatchdog` code in `solara.html.j2:315-319` references a global that
doesn't exist.)

### 6.4 Debug/test hooks on the `solara` JS global

The reconnect/remount machinery must be drivable and observable from tests (and from a
production devtools console). `kernel` and `widgetManager` are closure-locals in
`solaraInit` (`main-vuetify.js:130,233`), so exposing them costs a few assignments in
pip-shipped files — no CDN bundle change. Namespaced `solara.debug.*`, documented as
unstable, always-on (browser JS is reachable from devtools anyway; a reference adds no
capability, and production debugging is when it's most wanted):

- **Getters, not snapshots**: `solara.debug.kernel()`, `.widgetManager()`, `.ws()` — the
  socket is replaced on every reconnect and the widget manager on every soft-remount, so
  captured references go stale by design.
- **Actions**: `solara.debug.dropConnection()` — closes the underlying socket without
  disposing the kernel, so the jupyterlab-services reconnect machinery fires as on a
  network blip. (Implementation uses the vendored bundle's private `kernel._ws`; wrap
  defensively and warn if absent after a bundle upgrade. Fallback approach: intercept
  the `WebSocket` constructor in the debug module.)
- **Synchronization state** (the part that makes Playwright tests deterministic without
  sleeps): `solara.debug.connectionStatus`, `.reconnectCount`, `.remountCount` —
  counters, not booleans, so double-remounts (the flapping bug class, §6.2) are caught
  by assertion.
- **`solara.debug.lastRestore`** (DX review): `{status: "success"|"bailout"|"timeout"|
  "miss"|"fresh-schema", failedKey, cause}`, sent along with the app-status/remount
  flow. During the §6.5 simulate-failover practice this is the surface the author is
  already staring at — without it, a bail-out shows the *user* a dialog and shows the
  *developer* nothing until they grep server logs. Also distinguishes "normal deploy
  reset" from "something is wrong" (same visual outcome, opposite meanings).

Caveat: a client-side close simulates a *drop*, not a *migration*. The
fresh-instance test pairs `dropConnection()` with server-side arrangement: the real
two-process-shared-Redis setup (§9), or a cheap test-only route that evicts the
kernel from `contexts` (do **not** reuse `/_solara/api/close/...`, which marks the page
CLOSED and makes reconnection correctly refused, `kernel_context.py:226-227`).

The eviction route **fails closed** (security review — the existing close route,
`starlette.py:386-393`, is unauthenticated and keyed only on ids; do not replicate
that): enabled only when `settings.main.mode != "production"` AND the explicit test
setting is on — refuse to start (or warn loudly) if both production and enabled; the
route verifies session ownership (the same session-HMAC as restore) before evicting.
Otherwise a copy-pasted compose file turns it into an unauthenticated targeted
session-reset primitive.

Prior art in-repo: `tests/integration/reconnect_test.py:25-27` already drives reconnect
tests by closing the websocket **server-side** from a button
(`context.kernel.session.websockets[0].close()`) — the same pattern the multi-server
demo reuses (§9).

**`solara.debug.simulateFailover()`** combines both halves: drop the socket *and* (via a
dev/test-gated route) evict the kernel from `contexts` first, so the reconnect behaves
exactly like landing on a fresh instance — with only backend state surviving. Crucially,
this works in **single-process dev with the memory backend**: eviction removes the
in-memory kernel context, but the memory backend's hash (keyed by kernel id) survives in
the process, so restore runs for real. Every app author can exercise true failover
recovery with `solara run`, zero infrastructure. This is the cornerstone of §6.5.

### 6.5 The application recovery model — the honest weak point

Persistence restores opted-in reactives; everything else must be *re-derivable*. The
last hard problem is not mechanism but epistemics: **how does an author know their app
recovers correctly in any situation?**

**The invariant to teach** (this is the entire recovery contract): after failover, the
app is re-run from scratch as a pure function of

1. the **URL/route** (preserved by the client, §6.2),
2. the **persisted reactives** (restored before first render), and
3. **external sources of truth** (database, object store, APIs).

Everything else re-derives *automatically*, because the soft-remount re-runs the whole
component tree: `use_memo` recomputes, `use_task`/`use_effect` re-fire, `Computed`
recomputes. Recovering "the rest" from a calculation or a database refresh is therefore
not a recovery *hook* — it is the normal first render doing its normal job. A task keyed
on persisted inputs recomputes its dataframe from the DB on the new instance exactly as
it did on the original cold start. The discipline is: **persist inputs, recompute
outputs** — never persist what a task/memo derives, and never hold non-derivable truth
in a non-persisted reactive.

**The genuinely hard residue** (be honest in docs):

- *Non-derivable state that wasn't opted in* — lost, by definition. The fix is opt-in
  (or continuous save to the DB); no framework can conjure it back.
- *Mid-flight external side effects* — a wizard fired the step-3 email, state says
  step 3, but the failover happened mid-step. State is at-most-once; external effects
  need app-level idempotency. The `state_generation()` fencing token (§5.5b) is the
  tool for the strict cases.
- *In-flight input at the moment of the drop* — lost; v2 client-side replay (LiveView
  trick).
- *Background computation lost mid-run* — the task re-runs from scratch on remount;
  fine iff pure/idempotent.

**The epistemics answer: make failover testing trivial and continuous, because static
verification is impossible.** "Can my app recover?" has the same status as "is my app
correct after F5?" in classic session-based web frameworks — never provable, routinely
achieved through discipline plus cheap testing:

1. **One-click failover in dev** — `solara.debug.simulateFailover()` (§6.4) works on a
   single `solara run` process with the memory backend. The documented practice: walk
   every page of your app, trigger failover at each interesting state, verify what you
   see. Cheap enough to become habit, like checking hot-reload behavior.
2. **Optional dev mode: failover-on-reload** — a dev setting where the hot-reload path
   *also* goes through evict-and-restore instead of the in-process `state_save` pickle,
   so every code save exercises recovery continuously during development. (Optional,
   post-v1 — but it converts recovery from a launch-week audit into an ambient property.)
3. **CI recipe** — the Caddy round-robin integration test (§9) doubles as a template app
   authors copy to pin their own recovery behavior in CI.
4. **Documentation frame** — "fresh run with these values pre-set", never "resume". An
   author who designs pages to cold-start correctly from (URL, persisted inputs, DB) has
   recovery for free; an author who accumulates implicit in-memory sequence state does
   not, and no mechanism can fix that for them.

### 6.6 Where auth state lives (DX review — "does my login survive failover?")

For OAuth/solara-enterprise apps, authentication does **not** depend on this feature:
identity rides the session cookie / OAuth session middleware, which the browser
re-presents on reconnect regardless of which instance answers. What is lost on failover
is any *derived* user state held in non-persisted reactives (profile objects, role
caches) — re-derived on remount like any other computed state. Document this explicitly;
it is the first question every enterprise app author asks. When OAuth identity exists,
the restore gate should additionally bind to the authenticated user subject (§7), so a
stolen session cookie alone cannot restore another authenticated user's state.

## 7a. Observability (v1 requirement, not a follow-up)

The SRE review's hardest finding: solara has **no metrics infrastructure** ("emit a
metric" had nowhere to go), and the worst failure modes are *silent* — an open circuit
breaker stops producing errors precisely when persistence is off, and a fleet with
mismatched `secret_keys` fails every cross-instance restore quietly. A feature that can
silently turn itself off must announce itself. V1 ships:

- **A `state` block on the existing `/resourcez` endpoint** (`starlette.py:657` — it
  already reports websocket/kernel counters; no new metrics system needed). The five
  numbers that matter:
  1. `status` (`off | healthy | degraded`) + `circuit_breaker`
     (`closed | half_open | open`) — "is the feature on right now?"
  2. `backend_last_ok_age_seconds` + `backend_last_error`
  3. `restore_attempts / restore_success / restore_bailout` totals — the post-deploy
     restore hit-ratio is the number that says the feature works
  4. `flush_queue_depth` + `flush_failures_total`
  5. `superseded_closes_total` + `superseded_while_connected_total` — broken-stickiness
     / takeover-churn / attack detector
  6. **Sync volume** (added post-v1-review): `sync_count` / `sync_bytes_total` /
     `sync_mb_total` / `restore_bytes_total`, plus two top-N tables (`sync_by_key`
     aggregated across kernels — which VARIABLE costs the most — and `sync_by_kernel`,
     which session syncs the most; kernel ids truncated to an 8-char greppable prefix).
     Top 10 by default, top 100 with `?verbose=1`; tables capped at 500 entries with an
     `"(other)"` overflow bucket + drop counters (per-user key patterns are unbounded).
     Recorded only on ACKed writes so retried flushes never double-count.
- **A structured log spec** (stable event names, greppable, alertable; one line per
  event at a fixed level, always carrying `kernel_id` + a session hash):
  ```
  solara.state.restore  result=success|timeout|bailout|miss|fresh-schema kernel=… key=… cause=hmac|codec|skew
  solara.state.flush    result=ok|rejected|error kernel=… n_fields=…
  solara.state.breaker  transition=open|half_open|closed reason=…
  solara.state.close    reason=page-close|cull|superseded|server-shutdown deleted=true|false
  ```
- **`/readyz` stays backend-independent** (it is unconditional today, `server.py:75`,
  and must remain so): gating readiness on a *recovery cache* converts a Redis blip
  into a fleet-wide NotReady — a total main-path outage from a degraded recovery path.
  Backend health appears only on `/resourcez`.

Runbook seeds (docs deliverable): "dialogs after deploy" → expected iff the client
bundle changed (§6.1); else check `restore_bailout` rate, then `secret_keys` uniformity
across replicas (the #1 real-world cause of silent restore failure — no fleet-level
check exists, verify by hand), then `schema_tag` stragglers. "State not restoring" →
`/resourcez` state block first (`status`/breaker), then backend reachability, then
secret uniformity, then whether the variable had a stable explicit key.

## 7. Ops and security posture (documentation requirements)

- Redis: recommend `noeviction` + TTLs + memory alerting (with `allkeys-lru` a memory
  spike silently drops live sessions — the invisible worst case). Startup check logs the
  server's `maxmemory-policy`. Never share a `maxmemory allkeys-lru` cache instance.
- Managed Redis / Sentinel is enough; async-replication failover may lose last writes —
  acceptable for a recovery cache. Cluster: hash-tag `{kernel_id}` if ever needed.
- Sizing: ≈ concurrent sessions × opted-in state size; with JSON-first this is tens of
  KB/session (10k sessions ≈ hundreds of MB worst case).
- Security: HMAC-verified envelopes; Redis AUTH/ACL scoped to the prefix; TLS across
  networks; never internet-exposed; contents may include PII — treat as sensitive.
- Metrics: restore attempts/full/partial/miss; deserialize failures **by cause**
  (HMAC vs skew vs codec); serialize failures; blob-size histogram; write latency and
  queue depth; circuit-breaker state; restores/minute (reconnect-herd detector). The
  restore hit ratio after a rolling deploy is the number that says the feature works.
- Reconnect herd on deploys (all clients re-run + hit Redis + hit the app DB at once):
  client backoff already exists in jupyterlab-services; document the DB-side herd for
  app authors (LiveView's lesson).
- **Keep recommending sticky sessions as the routing fast path.** This feature is the
  recovery layer for what stickiness cannot cover: pod crash/OOM, autoscaler scale-in,
  spot reclamation, deploys with sessions outliving the drain window, AZ failover.
  Single-instance deployments should not enable it.

## 8. Prior art (why this shape)

- **Reflex** runs essentially this architecture in production (pickled state in Redis,
  per-substate keys, dirty-only writes, schema-hash discard-on-mismatch, per-token
  locks). Its production issues (unpicklable objects, lock expiry, remote-Redis
  flakiness) are precisely what opt-in + JSON-first + fencing-not-locking avoid.
- **Phoenix LiveView** persists nothing: remount re-derives from URL + signed identity +
  DB, and the client replays in-flight form input. The lesson adopted: persist the
  minimum source state, re-run to rebuild the rest; input-replay is the v2 candidate.
- **Shiny bookmarking** validates opt-in persist-inputs-and-re-run with exclusion of
  secrets and restore hooks. **NiceGUI** validates tiered opt-in storage with a
  first-class Redis backend and a two-knob lifetime (hot reconnect window vs long TTL).
- **Streamlit/Panel/Marimo** all punt (sticky sessions, accept loss) — shipping this well
  is a genuine differentiator.
- Rejected alternatives: event-sourcing/replay (needs determinism across the very code
  versions a deploy changes), CRDTs (no sustained multi-writer), whole-kernel
  serialization/CRIU (threads/sockets/comms don't serialize), live kernel handoff (only
  works when the old instance is alive — the case already covered by the flush).

## 9. Feasibility and plan

All four reviews independently landed on **doable-with-care**. The architecture is
favorable: a single write choke point, a lazy-init seam that makes restore "have the
value present before first read", one clean-close convergence point, an existing
clean-vs-lost-connection distinction, and a client mount pipeline that can be re-executed
without touching the CDN bundles.

**Decided: one PR, staged as ~4 commits** (each commit coherent and green, so the PR
reads as the plan):

1. **Commit 1 — core state layer (no Redis, no server changes)** *(shipped: f12e6e25)***:** `StateBackend`
   four-verb protocol (§5.7) + memory backend (envelope-byte fidelity) +
   `state_backend_map` registry, settings + startup validation (secrets, pickle gate),
   `persist=`/`key=` on `solara.reactive()` + key auto-derivation (`executing` +
   `__set_name__`) + collision registry + the specified refusal error message,
   envelope codecs (strict JSON with the §4.2 coercion set: datetime/date/enum/numpy
   scalar/UUID/Decimal/set; gated pickle; HMAC-SHA-256 + canonical context binding +
   key rotation), **subscribe_change-based dirty-tracking** (no `set()` edit),
   lazy restore-at-init seam with explicit `StoreValue` wrapper reconstruction (both
   mutation-detection modes), all-or-nothing bail-out semantics (§4.3). Unit tests: the
   derivation refusal matrix (factories, loops, tuple targets, no-source), collision
   detection, restore-skips-default in both wrapping modes, bail-out on one bad
   envelope, codec failures + coercion matrix, `Ref` field writes dirty the root,
   snapshot-then-serialize under concurrent mutation, keys-stay-dirty-until-ACK.
2. **Commit 2 — server lifecycle** *(shipped: bd1b749b)***:** takeover in `initialize_virtual_kernel`
   (verify-then-bump-then-read atomically, no-write-on-miss, claim-or-delete on
   fresh-start, kernel_id UUID validation, reuse-branch ownership check), write-behind
   worker (context-entering, snapshot-under-lock) + debounce + specified circuit
   breaker (gates restores too), reason-gated fenced `DEL`, orphan-cull knob (shared
   backend only), bounded rejection protocol (one re-takeover per epoch, then concede),
   bounded+batched SIGTERM flush + `timeout_graceful_shutdown`, `close_reason` +
   `solara.kernel_closed_event()` + `solara.state_generation()`, fail-closed
   kernel-eviction route, **the `/resourcez` state block + structured log spec (§7a)**.
   Tests: memory backend + eviction gives **single-process failover simulation**
   (restore-for-real without Redis, §6.4) — covers restore, bail-out + poisoned-hash
   deletion, rejection/concede, and the fast double reconnect (A → B → A with A's
   context still live) largely as unit/light-integration tests.
3. **Commit 3 — Redis backend** *(shipped: 2b2ec1d9)***:** `state/redis.py` in core (lazy `import redis`), Lua
   atomic takeover + fenced pipeline writes, TTL refresh. CI gains a Redis service;
   integration test: two solara-server processes sharing Redis, kill/evict one
   mid-session, reconnect to the other.
4. **Commit 4 — client soft-remount + demo + docs** *(shipped: this PR)***:** inline app-status probe,
   `canRecover`/`appVersion`, remount sequence, `remountKey`, UX polish, popout/SSG
   handling, `solara.debug.*` hooks incl. `simulateFailover()` (§6.4). **Caddy
   round-robin demo** — one artifact serving as demo, integration test, and
   documentation: a Caddyfile (`lb_policy round_robin`, two `solara run` backends, one
   Redis) + a demo app with a "Disconnect" button using the server-side-close pattern
   from `tests/integration/reconnect_test.py:25-27`; round robin assigns per
   *connection*, so the reconnect lands on the other instance. Playwright drives it:
   build up state, disconnect, assert soft-remount (`solara.debug.remountCount === 1`,
   no dialog, persisted state intact, derived state recomputed). Docs: deployment guide
   (Redis ops, eviction policy, sizing, sticky-sessions-as-fast-path), the recovery
   model guide (§6.5), at-most-once semantics stated plainly.

**v2 candidates:** `on_restore` hook; client-side in-flight input re-send (LiveView
trick); session-scoped storage (survive F5); Prometheus-style metrics endpoint (§7a's
`/resourcez` block is the v1 substitute); `owns_state()` active probe (§5.5b —
`state_generation()` moved to v1); failover-on-reload dev mode (§6.5); per-variable
`version`/`migrate` (§4.1 — cut from v1); recipes page expansion.

**Scope note (maintainer review, recorded):** the realistic total is ~2.5-3.5k LOC of
product code plus a comparable test volume — a large PR. The maintainer reviewer
recommended splitting (client-remount first, then core persistence, then Redis) and
cutting auto-derivation and fencing from v1 entirely; the decision stands to ship as
one staged PR with derivation and fencing included (fencing's cost dropped
substantially with the concede-based rejection protocol replacing the reclaim state
machine), but the commit boundaries above are deliberately chosen so the PR can be
split along them if review demands it. Budget explicit stabilization time for the
Caddy/Playwright CI topology — a new two-process+Redis+proxy harness is a known
flaky-test source (cf. the existing Windows integration flakiness in CLAUDE.md).

## 10. Risk register (top items)

| Risk | L | I | Mitigation |
| --- | --- | --- | --- |
| Deploy-time version skew: old envelopes vs new code — triggered by the exact event the feature serves | H | M | global version tag → clean whole-state discard + fresh soft-remount (live redeploy works); unexpected decode failure → visible bail-out (§4.3); skew metric; docs |
| Serialization failures in prod (wrong objects reach opted-in vars) | H | M | strict JSON codec fails deterministically on first write in dev; prod: ERROR + delete hash + stop persisting (no partial snapshots); 1 MB warn |
| Redis down degrades worse than the disease (timeouts on every interaction) | M | H | write-behind off-thread; circuit breaker; 300 ms restore deadline then fresh |
| Redis compromise ⇒ RCE via pickle | L | C | HMAC-verify before deserialize; JSON default; pickle per-var opt-in; ACL/TLS |
| Split-brain: old kernel's background task clobbers restored state | M | M | generation fence + rejected-write self-cull + short orphan cull |
| Unstable auto keys silently mixing variables | H (if allowed) | H | keys are explicit or derived only from statically unambiguous definition sites (module-level single-name assignment, class attribute); all ambiguous cases raise demanding `key=` |
| Blocking I/O under store locks (deadlock precedent) | M (if careless) | H | dirty-mark only in `set()`; all I/O on worker threads at flush boundaries |
| Reconnect herd on deploy (Redis + app DB) | M | M | pipelined reads, client backoff exists, document DB herd |
| Crash loses last debounce window (user saw N+1, gets N) | M | L-M | small debounce window + graceful-teardown flush; document at-most-once |
| Semantic mismatch by design: restored (opted-in) vars coexist with reset (non-opted-in) vars and re-run effects | M | M | values present before first render; the recovery model + simulate-failover practice (§6.5); docs framing "fresh run with values pre-set", not "resume"; `on_restore` hook (v2). Failure-induced partiality is eliminated by the all-or-nothing bail-out (§4.3) |

## 11. Decisions log (resolved) and remaining opens

Resolved:

1. **Placement:** everything in core solara-server; Redis backend included with lazy
   import. No solara-enterprise involvement.
2. **No `solara.lab` gating** — stable API on `solara.reactive()` / `solara.*`.
3. **Serializer:** strict JSON default + explicit per-variable pickle opt-in.
4. **`auto_remount`:** yes — soft-remount available without any backend for apps whose
   state is fully URL/DB-derived.
5. **Restore failure:** all-or-nothing bail-out → hard-refresh dialog ("we lost",
   visibly), §4.3. Global version-tag mismatch stays the graceful path (live redeploy =
   clean state reset + soft-remount).
6. **Delivery:** one PR, ~4 staged commits (§9), with the Caddy round-robin setup as
   combined demo/test/documentation.

7. **Version semantics** (was open, resolved by the SRE review): two separate concepts —
   `schema_tag` (server-side envelope compatibility; mismatch → clean reset +
   soft-remount) and `clientVersion` (opaque asset hash; mismatch → hard refresh).
   §6.1. `schema_tag` defaults to derived-from-solara-version, user-overridable.

Still open:

8. **Derivation failure: raise vs warn.** Proposal: raise `ValueError` (silent wrong
   keys are the top risk); optionally a settings escape hatch downgrading to
   warn-and-skip-persistence for that variable.
9. **Bail-out storm valve threshold** (`bailout_storm_threshold`): default 50% of
   restores in a sliding window — needs a real default picked during implementation.

## 12. Revision 2 — adversarial review changelog

Five persona reviews (distributed-systems skeptic, minimalist maintainer, security,
app-developer DX, SRE) ran against revision 1. Confirmed blockers, all fixed in this
revision:

1. **HMAC bound to `__generation__`** (dist-sys + security, independently): takeover
   bumps the generation before the restore read, so every failover would fail HMAC →
   all-or-nothing bail-out → the feature could never restore anything. Fixed: generation
   removed from the signature; fencing (writes) and integrity (HMAC) share no inputs
   (§4.2, §5.2).
2. **Unconditional `DEL` in `close()`** (dist-sys + SRE, independently): `on_shutdown`
   closes every context on SIGTERM → every rolling deploy wiped all state; the
   superseded path deleted the hash the new owner was using; the orphan cull deleted
   what it promised to preserve. Fixed: `DEL` only on `page-close`, fenced; all other
   reasons flush-and-leave-for-TTL (§5.4).
3. **Takeover wrote before verifying** (security): unauthenticated Redis key-flooding
   via random `?kernelid=` + victim takeover-DoS by generation-bumping. Fixed:
   verify-inside-the-Lua, never write on a miss, hash created only by the first
   legitimate flush; kernel_id UUID-validated at the websocket entry (§5.1).
4. **Reclaim-iff-connected livelock** (dist-sys): `page_status` reflects *observed*
   disconnects, so half-open TCP / cross-instance multi-tab put multiple instances in
   "I hold the socket" and the reclaim rule looped `HINCRBY` + full re-flush unbounded.
   Fixed: bounded rejection protocol — one re-takeover per connection epoch, then
   concede-but-serve, loudly logged (§5.5).

Majors folded in: zombie-hash resurrection after restore-timeout/version-discard
(claim-or-delete, §5.1); unfenced pipeline variant removed (§5.5); identity-field write
path specified + missing `__session_id__` = hard reject (§5.1); torn-serialize fixed by
snapshot-under-lock (§4.4); keys-stay-dirty-until-ACK (§4.4); flush worker must enter
the kernel context (§5.3); no I/O under `context.lock` at teardown + bounded batched
SIGTERM flush + `timeout_graceful_shutdown` (§5.3); poisoned-hash deletion at bail-out
+ bail-out storm valve (§4.3); TOCTOU on the reuse branch closed via the rejection
protocol (§5.1); dedicated rotatable `SOLARA_STATE_SECRET_KEYS` + deployer-side pickle
gate + HMAC algorithm/canonicalization spec (§4.2); `http_only` default + credential
co-logging fixes (§5.6); fail-closed eviction route (§6.4); memory-backend envelope
fidelity (§5.7); observability as a v1 requirement — `/resourcez` state block +
structured log spec, `/readyz` untouched (§7a); two-versions split (§6.1); StoreValue
wrapper reconstruction acknowledged as real work + subscribe-based dirty-marking
(§4.4); default-codec coercion set + refusal-message spec + store-pattern recipe + auth
clarification + `solara.debug.lastRestore` (DX, §4.1/§4.2/§6.4/§6.6);
`state_generation()` promoted to v1 (§5.5b); orphan cull gated on shared backend +
honesty about the shortened hot-reconnect window (§5.4).

Recorded dissent (not adopted): the maintainer reviewer would cut fencing and key
auto-derivation from v1 and split the PR; overruled by explicit project decisions, with
commit boundaries kept split-friendly and fencing simplified to the concede protocol.

Reviewer verdicts on revision 1: "not shippable as designed" (dist-sys), "conditional
no-go" (SRE), "must not ship as written" (security) — all with the same conclusion that
the architecture is right and the fixes are cheap and convergent. This revision applies
all of them; the design should get one more skim-review of §5.1/§5.4/§5.5 (the rewritten
sections) before implementation starts.
