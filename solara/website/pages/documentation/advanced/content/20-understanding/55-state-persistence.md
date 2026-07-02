---
title: State persistence and failover recovery
description: Opt selected reactive variables into a shared backend (Redis) so that a browser
    that reconnects to a different server instance recovers transparently, without a page refresh.
---
# State persistence and failover recovery

## The problem

A Solara [virtual kernel](/documentation/advanced/understanding/solara-server#virtual-kernels)
is stateful: each browser tab owns a kernel on one server instance, holding its widget tree,
reactive values and hook state. Behind a load balancer a websocket reconnect can land on a
*different* instance, which has no kernel for that kernel id. Today the client then shows the
blocking *"Could not restore session. Please refresh."* dialog and all state is lost.

[Sticky sessions](/documentation/advanced/understanding/solara-server#handling-multiple-workers)
keep a client pinned to its original instance and remain the routing fast path. But stickiness
cannot cover the cases where the original instance is *gone*: a pod crash or OOM kill, an
autoscaler scale-in, spot-instance reclamation, an availability-zone failover, or a rolling
deploy whose sessions outlive the drain window.

State persistence is the **recovery layer** for exactly those cases. You opt selected reactive
variables into a shared backend (Redis). When a reconnect lands on a fresh instance, that
instance restores the opted-in values from the backend and the client re-mounts in place — same
URL, opted-in state intact, no refresh dialog.

### When to enable it

- **Multi-instance deployments** where sessions can outlive the instance that created them
  (Kubernetes, autoscaling groups, rolling deploys, spot instances).

### When *not* to enable it

- **Single-instance deployments.** With one process the kernel and its state die together;
  there is nothing on another instance to recover to, and enabling a networked backend only
  adds latency and a shortened orphan-cull window (see
  [the deployment guide](/documentation/getting_started/deploying/state-persistence)). Keep it
  off (the default).

Persistence is **opt-in per reactive variable**. Most state is derived, or cheaply recoverable
from a database, and much of it does not serialize well. You declare what actually matters.

## Enabling persistence

Persistence is off until you configure a backend. In production that backend is Redis — see
[Scaling out with state persistence](/documentation/getting_started/deploying/state-persistence)
for the full Redis, security and ops story. For local development you can use the in-process
`memory` backend, which stores the same signed envelope bytes Redis would (see
[Testing failover in development](#testing-failover-in-development) below).

The minimum to turn it on:

```bash
export SOLARA_STATE_BACKEND=redis
export SOLARA_STATE_URL=redis://localhost:6379/0
export SOLARA_STATE_SECRET_KEYS="a-long-random-secret"   # REQUIRED whenever a backend is enabled
```

A [full configuration reference](#configuration-reference) is at the bottom of this page.

## The API

Persistence is a keyword on the existing [`solara.reactive`](/documentation/api/utilities/reactive):

```python
import solara

count = solara.reactive(0, persist=True, key="myapp.count")
```

`persist=True` opts the variable in; `key=` is its **stable, cross-process persistence key**.
The same key must resolve to the same variable across every instance and every deploy, so an
explicit `key=` is the norm for anything meant to be long-lived (it survives file moves and
renames).

### Derived keys (prototype convenience)

If you omit `key=`, Solara derives one from the *definition site* — but only for the two
statically unambiguous patterns:

```python
import solara

# module-level single-name assignment -> key "myapp.pages:count"
count = solara.reactive(0, persist=True)


class Settings:
    # class attribute -> key "myapp.pages:Settings.theme"
    theme = solara.reactive("light", persist=True)
```

Derived keys are name-only (no line numbers), so reformatting is safe. But **renaming or moving
the variable changes the derived key, which discards the old state** (a clean reset — the same
semantics as a schema-tag bump, below). Each auto-derived key is logged once at INFO
(`derived persistence key "myapp.pages:count"`), so a rename-induced reset is greppable. Use
derived keys for prototyping; switch to an explicit `key=` before you rely on the state.

### The factory refusal

Anything ambiguous — a reactive created inside a function, factory, loop, conditional, a
tuple/attribute target, or a source-less environment — **raises `ValueError`** demanding an
explicit key, rather than silently guessing. This is deliberate: the naive "fix" of a constant
key inside a factory would make *every user session share one backend field*, disclosing one
user's state to another on restore.

```python
def make_query_state():
    return solara.reactive("", persist=True)   # raises: no stable per-instance key
```

The error names the definition site and shows the correct per-instance fix:

```
persist=True requires an explicit key= here: a reactive created inside a function or
factory produces one instance per call; instances cannot share a key.
Definition site: myapp/state.py:42: `return solara.reactive("", persist=True)`
Give each instance a unique key, e.g.:  solara.reactive(..., persist=True, key=f"user:{user_id}:query")
NEVER use a constant key for reactives created per-instance - instances would overwrite each other's state.
```

### The store pattern

Solara's [store pattern](/documentation/getting_started/fundamentals/state-management#creating-a-store)
creates reactives inside `__init__`, which the derivation refuses (one store instance per call).
Give each reactive a **per-instance key** built from an id you already have:

```python
import solara


class UserQueryStore:
    def __init__(self, user_id: str):
        prefix = f"user:{user_id}"
        self.query = solara.reactive("", persist=True, key=f"{prefix}:query")
        self.page = solara.reactive(0, persist=True, key=f"{prefix}:page")
```

The `user_id` discriminator is what keeps two users' stores in two different backend fields.
Never use a constant key here.

### `PersistConfig`

`persist=True` is sugar for `persist=solara.PersistConfig(key=..., serializer="json")`. Pass a
`PersistConfig` when you need a non-default serializer:

```python
import solara

filters = solara.reactive(
    {"country": "NL", "year": 2024},
    persist=solara.PersistConfig(key="myapp.filters", serializer="json"),
)
```

`PersistConfig` has exactly two fields: `key` and `serializer`. An explicit `key=` argument
always wins over `PersistConfig.key`.

## Serialization

Every persisted value is serialized by a *codec* and wrapped in an HMAC-signed envelope that is
verified before anything is ever deserialized.

### The default JSON codec

The default `"json"` codec is strict but coerces the types that come straight out of real
widget, filter and form state. It round-trips:

| Type | Result |
| - | - |
| `None`, `bool`, `int`, `float`, `str` | round-trips faithfully |
| `list`, `dict` (with the members below) | round-trips faithfully |
| `set`, `frozenset` | round-trips faithfully |
| `datetime.datetime` / `date` / `time` | round-trips faithfully (ISO format) |
| `uuid.UUID`, `decimal.Decimal` | round-trips faithfully |
| `bytes` | round-trips faithfully (base64) |
| `enum.Enum` (incl. `IntEnum` / `StrEnum`) | round-trips faithfully |
| **Pydantic `BaseModel`** (v2, v1 fallback) | round-trips faithfully (self-describing, see below) |
| **`dataclass` instances** (incl. nested) | round-trips faithfully (self-describing, see below) |
| `tuple` | **coerced to `list`** (JSON has no tuple type) |
| `bytearray` | coerced to `bytes` |
| `numpy` integer / float scalar | coerced to Python `int` / `float` |

Anything else raises a `SerializeError`. The strict codec fails deterministically on the *first*
write, so you hit it immediately in development, never silently in production. For exotic
objects, register a custom codec (see below).

### Pydantic models and dataclasses

Models and dataclasses are **self-describing**: the envelope records the class
(`module:qualname`) *with* the value, so deserialization never needs a type declared anywhere —
which is exactly what makes the common `Optional[Model]` pattern work:

```python
user = solara.reactive(None, persist=True, key="myapp.user")  # holds None or a User
```

When a `User` lands in the reactive, the envelope tags it; on restore the class is imported,
checked (only `BaseModel` subclasses and dataclasses are ever instantiated — never an arbitrary
class), and validated with `model_validate` (pydantic) or reconstructed field-by-field
(dataclasses; `init=False` fields are recomputed by `__post_init__`, not stored). Nested
dataclasses, enums and dates inside models all round-trip. **Containers of models work too**:
a reactive holding `[User, User]` — or models nested in dicts/lists at any depth — restores
real model instances, because every element carries its own tag (a *tuple* of models comes
back as a list of models, the usual tuple caveat). Pydantic semantics are preserved
exactly: a typed field (`members: list[User]`) reconstructs its models, an untyped `list` field
round-trips to dicts — the same as pydantic's own `model_validate(model_dump())`. (Untyped
*dataclass* fields do reconstruct models — dataclass fields go through solara's recursive
tagging rather than `model_dump()`.)

Two caveats:

> **Renaming or moving a persisted class breaks old envelopes** (the stored `module:qualname`
> no longer resolves) — the restore bails out and the user gets the refresh dialog. Bump
> `SOLARA_STATE_SCHEMA_TAG` when you rename model classes for a clean reset instead.

> **Model shape changes follow pydantic rules**: added *optional* fields are compatible; a new
> *required* field makes old envelopes fail validation (bail-out). Breaking shape changes are
> what the schema tag is for. Validators and `__post_init__` run during restore, so keep them
> side-effect-free.

> **Watch out for the `tuple` -> `list` round trip.** A reactive holding a `tuple` restores as a
> `list`. If your code branches on `isinstance(x, tuple)`, normalize on read or hold a `list`.

> **In-place mutation is not persisted.** With
> [mutation detection](/documentation/getting_started/fundamentals/state-management#mutation-pittfalls)
> off (the production default), mutating a persisted value in place (`items.value.append(...)`)
> fires no change and is therefore never persisted. The existing "re-assign, don't mutate" rule
> becomes load-bearing here: `items.value = [*items.value, x]`.

### Custom codecs

Register a `(dumps, loads)` pair under a name and select it with `serializer=`. Use this for
types the JSON codec does not cover, or when you want rename-robust envelopes (a custom codec
names its class in *code*, not in the stored data, so renaming the class cannot break old
envelopes as long as the codec keeps up):

```python
import json
import solara
import solara.state


solara.state.register_codec(
    "geo",
    lambda value: value.to_wkb(),
    lambda blob: shapely.from_wkb(blob),
)

area = solara.reactive(
    DEFAULT_AREA, persist=solara.PersistConfig(key="myapp.area", serializer="geo")
)
```

### The `pickle` codec

`serializer="pickle"` is fast and general but version-skew fragile, and — because pickle
executes arbitrary code on load — an RCE risk if the backend is ever compromised. It is
therefore behind a **deployer-side gate**: it raises unless the *deployment* sets
`SOLARA_STATE_ALLOW_PICKLE=true`. Application or library code cannot silently opt a deployment
into a pickle-deserialize path. The HMAC envelope narrows the exposure ("Redis write access"
alone is not enough — an attacker also needs the app secret), but JSON or a custom codec is the
safer default. Prefer them.

## The recovery model

This is the heart of using persistence well. Persistence restores your opted-in reactives;
**everything else must be re-derivable**.

### The invariant

After a failover, your app is **re-run from scratch** as a pure function of:

1. the **URL / route** (preserved by the client on reconnect),
2. the **persisted reactives** (restored before the first render), and
3. **external sources of truth** (your database, object store, APIs).

Everything else re-derives *automatically*, because the re-mount re-runs the whole component
tree: `use_memo` recomputes, `use_task` / `use_effect` re-fire, `Computed` recomputes. A task
keyed on persisted inputs recomputes its dataframe from the database on the new instance exactly
as it did on the original cold start. Recovering "the rest" is not a special recovery hook — it
is the normal first render doing its normal job.

The discipline in one line: **persist inputs, recompute outputs.** Never persist what a
task or memo derives, and never hold non-derivable truth in a non-persisted reactive.

### The honest residue

Be aware of what does *not* come back for free:

- **Non-derivable state you did not opt in** is lost, by definition. The fix is to opt it in (or
  save it continuously to a database). No framework can conjure it back.
- **Mid-flight external side effects.** A wizard fired the step-3 email, state says step 3, but
  failover happened mid-step. State is *at-most-once*; external effects need app-level
  idempotency. Use [`solara.state_generation()`](#fencing-external-side-effects) as a fencing
  token for the strict cases.
- **In-flight input at the moment of the drop** (the keystroke you were typing) is lost.
- **A background computation lost mid-run** re-runs from scratch on re-mount — fine as long as
  it is pure/idempotent.

### Fencing external side effects

`solara.state_generation()` returns a monotonically increasing epoch for this kernel (it needs
no backend round trip). It increases on every failover, and returns `None` when persistence is
off or this instance does not own the state. Pass it into your own external writes so that a
*superseded* instance — an old kernel whose background task comes back to life after another
instance took over — cannot re-apply a stale effect:

```python
import solara

order_id = solara.reactive("", persist=True, key="checkout.order_id")


def charge():
    epoch = solara.state_generation()  # increases on failover; None when unowned
    payment.charge(
        order_id=order_id.value,
        idempotency_key=order_id.value,  # stable across a re-run -> charged at most once
        fencing_epoch=epoch,             # lets the payment service reject an older instance
    )
```

The idempotency key (derived from persisted state) makes a *re-run* safe; the fencing epoch lets
your external system reject a write from a superseded, lower-epoch instance.

### Failure semantics

Two outcomes are treated deliberately differently on reconnect:

- **Schema reset (expected, graceful).** If the persisted value shape changed — a live redeploy,
  a new Solara version, or an explicit `SOLARA_STATE_SCHEMA_TAG` bump — the whole stored hash is
  discarded, the kernel starts fresh, and the client **soft-remounts** into fresh state. Live
  redeploys "just work", with a clean state reset. No dialog.
- **Bail-out (unexpected, visible).** If any restored envelope fails HMAC verification or
  decoding, restore is **all-or-nothing**: it discards *everything*, deletes the poisoned hash
  (so a bookmarked kernel id cannot loop forever), and the client shows the refresh dialog. A
  partially restored app — some variables restored, others silently at defaults — is a state no
  author ever tested; a visible "we lost, please refresh" is more honest than a silently
  inconsistent app.

Because writes are debounced and best-effort, the guarantee is **at-most-once**: on failover you
get your state back as of at most the flush-debounce window before the disconnect — when the
disconnect is observed or the shutdown is graceful. A hard kill or a silent network drop can
lose a little more.

### Testing failover in development

Static verification is impossible — "can my app recover?" has the same status as "is my app
correct after F5?" It is achieved through discipline plus cheap, continuous testing.

You can exercise *real* failover in a single `solara run` process, with zero infrastructure,
using the in-process `memory` backend plus a dev-only eviction route:

```bash
export SOLARA_STATE_BACKEND=memory
export SOLARA_STATE_SECRET_KEYS="dev-secret"      # required for any backend, including memory
export SOLARA_STATE_TEST_EVICTION=true            # dev/test only; refused in production
solara run myapp.py
```

Then, from the browser devtools console, run:

```javascript
solara.debug.simulateFailover()
```

This evicts the in-memory kernel *and* drops the socket, so the reconnect behaves exactly like
landing on a fresh instance — only backend state survives, and restore runs for real.

The documented practice: **walk every page of your app, trigger a failover at each interesting
state, and verify what you see.** Cheap enough to become habit, like checking hot-reload. If a
value you expected is gone, opt it in (or make sure it re-derives from URL + persisted inputs +
database).

## Stopping user threads cleanly

If you spawn your own threads, capture the kernel's closed event *inside the kernel context* at
spawn time and stop when it fires. This covers every close reason — a supersession or cull, not
just a tab close:

```python
import threading
import solara


def start_worker():
    closed = solara.kernel_closed_event()  # capture inside the kernel context

    def run():
        while not closed.is_set():
            do_some_work()
            closed.wait(timeout=1.0)

    threading.Thread(target=run, daemon=True).start()
```

## Configuration reference

Every setting is read from an environment variable with the `SOLARA_STATE_` prefix (or a `.env`
file).

| Environment variable | Default | Meaning |
| - | - | - |
| `SOLARA_STATE_BACKEND` | `""` (disabled) | Backend name: `redis`, `memory`, or empty to disable persistence. |
| `SOLARA_STATE_URL` | `""` | Backend DSN, e.g. `redis://localhost:6379/0`. |
| `SOLARA_STATE_SECRET_KEYS` | `""` | Comma-separated HMAC keys (verify-any, sign-first). **Required** and must be non-default whenever a backend is enabled. |
| `SOLARA_STATE_ALLOW_PICKLE` | `False` | Deployer gate for `serializer="pickle"`; it raises without this. |
| `SOLARA_STATE_TTL` | (`kernel.cull_timeout`, 24h) | Backend key lifetime, refreshed on every write and on connect. |
| `SOLARA_STATE_ORPHAN_CULL_TIMEOUT` | `5m` | How long a disconnected kernel lives before culling — applies only with a shared backend. |
| `SOLARA_STATE_PREFIX` | `solara:state:` | Backend key prefix / table name. |
| `SOLARA_STATE_FLUSH_DEBOUNCE` | `300ms` | Coalescing window for write-behind flushes; also the at-most-once loss window. |
| `SOLARA_STATE_CONNECT_TIMEOUT` | `0.3` | Hard cap (seconds) on any takeover/flush backend call. |
| `SOLARA_STATE_BREAKER_FAILURES` | `3` | Consecutive backend failures before the circuit breaker opens. |
| `SOLARA_STATE_BREAKER_WINDOW` | `30s` | How long the breaker stays open before a half-open probe. |
| `SOLARA_STATE_SCHEMA_TAG` | `""` (derived from the Solara version) | Value-shape tag; a mismatch triggers a clean state reset + soft-remount. |
| `SOLARA_STATE_AUTO_REMOUNT` | `None` (on iff a backend is set) | Force client soft-remount on/off. |
| `SOLARA_STATE_BAILOUT_STORM_THRESHOLD` | `0.5` | Fraction of restores that may bail out before the dialog is suppressed and the fleet degrades to a silent fresh start. |
| `SOLARA_STATE_TEST_EVICTION` | `False` | Enables the dev/test kernel-eviction route for `simulateFailover()`; refused in production mode. |
