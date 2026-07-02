---
title: Scaling out with state persistence (Redis)
description: Run Solara across multiple instances and recover sessions after a crash, scale-in or
    deploy by persisting opted-in reactive state to a shared Redis backend.
---
# Scaling out with state persistence

When you run Solara across multiple instances, a websocket reconnect can land on an instance that
never held the session's kernel. [Sticky sessions](/documentation/advanced/understanding/solara-server#handling-multiple-workers)
keep clients pinned to their original instance and remain the routing fast path — but they cannot
help when that instance is *gone*: a crash or OOM kill, an autoscaler scale-in, spot reclamation,
an AZ failover, or a rolling deploy whose sessions outlive the drain window.

State persistence is the **recovery layer** for those cases. Opted-in reactive variables are
written to a shared Redis backend; when a reconnect lands on a fresh instance it restores them and
the client re-mounts in place. See
[State persistence and failover recovery](/documentation/advanced/understanding/state-persistence)
for the application-side API and — importantly — the *recovery model* your app must follow. This
page is the operations side.

> **Single-instance deployments should not enable this.** With one process the kernel and its
> state die together; a networked backend only adds latency and a shorter orphan-cull window.

## Enabling Redis

Install the Redis client (imported lazily, only when the backend is `redis`):

```bash
$ pip install redis        # or:  pip install "solara-ui[redis]"
```

Then point Solara at your Redis and set the secret keys:

```bash
export SOLARA_STATE_BACKEND=redis
export SOLARA_STATE_URL=redis://localhost:6379/0
export SOLARA_STATE_SECRET_KEYS="a-long-random-secret"
```

The server validates this configuration at startup and refuses to start on a misconfiguration
(missing secrets when a backend is enabled, or `SOLARA_STATE_ALLOW_PICKLE=true` with default
secrets).

### Valkey, KeyDB and Dragonfly

The Redis backend speaks the Redis protocol through `redis-py`, so it works transparently on
**Valkey, KeyDB and Dragonfly** as well — useful since much managed "Redis" is Valkey after the
license fork. Managed Redis or Redis Sentinel is sufficient; async-replication failover may lose
the last few writes, which is acceptable for a recovery cache. For Redis Cluster, the per-kernel
hash is a single key, so it lives in one slot.

## Secret keys and rotation

`SOLARA_STATE_SECRET_KEYS` signs every stored value with HMAC-SHA-256, verified *before* anything
is deserialized. It is **required and must be non-default** whenever a backend is enabled. It is a
dedicated secret — deliberately *not* your session/OAuth cookie secret — so that one secret does
not span cookie forgery, state tampering and (if you enable pickle) code execution.

**Every instance in the fleet must use the same keys.** Mismatched keys across replicas are the
single most common cause of silent restore failure: cross-instance restores fail HMAC
verification and bail out on one side of the fleet only, with no automatic fleet-wide check.

The setting is a **comma-separated list**, which enables zero-downtime rotation. Verification
accepts **any** listed key; new envelopes are always signed with the **first**. Rotate in two
phases so both old and new instances can verify each other during the roll:

1. **Add-new-verify-only** — prepend the new key, keep the old:
   `SOLARA_STATE_SECRET_KEYS="new-secret,old-secret"`. New writes are signed with `new-secret`;
   envelopes signed with `old-secret` still verify. Roll this out to the whole fleet.
2. **Drop-old** — once every instance signs with the new key and old-signed envelopes have aged
   out (past the TTL): `SOLARA_STATE_SECRET_KEYS="new-secret"`.

## Redis memory and eviction policy

The recovery backend must **never** double as a shared `allkeys-lru` cache. Under memory pressure
an LRU policy would silently evict *live* session state — the invisible worst case.

Configure the Redis instance with:

- `maxmemory-policy noeviction` — refuse writes rather than evict live sessions. Solara already
  puts a TTL on every key, so abandoned sessions are reclaimed without eviction.
- A **memory alert** well below `maxmemory`, so you scale before `noeviction` starts rejecting
  writes (a rejected write degrades gracefully — see [Degraded mode](#degraded-mode) — but it is a
  signal to size up).
- A dedicated Redis instance (or at least a dedicated database / key namespace via
  `SOLARA_STATE_PREFIX`), scoped with Redis AUTH/ACL, TLS across networks, and never exposed to
  the internet. Persisted state may contain PII — treat it as sensitive.

Solara logs the server's `maxmemory-policy` at startup so a misconfigured `allkeys-lru` is visible.

### Sizing

A rule of thumb: **memory ≈ concurrent sessions × opted-in state per session**. With the JSON-first
codec, opted-in state is typically tens of KB per session, so 10,000 concurrent sessions is on the
order of hundreds of MB worst case. Large dataframes do not belong here — persist a *reference*
(an id, a URL) and recompute the frame from your database on restore.

## Lifetime: TTL versus culling

Two independent timers govern how long state lives:

- **Backend TTL** (`SOLARA_STATE_TTL`, default the 24h `kernel.cull_timeout`) is refreshed on
  every write and on every connect. This is how long a session's state survives in Redis after the
  last activity, and therefore how long a late reconnect can still restore.
- **Orphan cull** (`SOLARA_STATE_ORPHAN_CULL_TIMEOUT`, default `5m`) is how long a *disconnected*
  in-memory kernel is kept alive on an instance before it is culled. With a shared backend there
  is no reason to hold an orphaned kernel in memory for 24h — its state is safe in Redis.

**The honest trade:** the shortened orphan cull is exactly what reduces the same-instance
live-kernel window from 24h to ~5m. A slow reconnect *within* 5m (to the same instance) still gets
everything, including non-persisted state. A reconnect *after* 5m gets only the opted-in state
back — which is the intended behavior for multi-instance, and precisely why the recovery model
matters. (For single-instance / `memory`-backend setups this shortened cull does not apply; state
and kernel die together, so shortening would only lose state.)

State is deleted from Redis only on a genuine tab close (a fenced delete). Culls, supersessions and
server shutdown **flush-and-leave** the state for the TTL to reclaim — so the state survives the
exact events (deploys, scale-in) the feature exists for.

## Graceful shutdown

The final best-effort flush on shutdown only runs if uvicorn's lifespan teardown runs — and
uvicorn waits for connections **indefinitely** by default, so a lingering websocket can stall the
drain until Kubernetes SIGKILLs the pod and nothing flushes. Set uvicorn's
`--timeout-graceful-shutdown` (comfortably below your `terminationGracePeriodSeconds`) so the
drain is bounded; the shutdown flush is one bounded, batched pass over all sessions.

A clean tab-close, client-initiated close, observed TCP reset and lifespan shutdown all get a final
flush. An OOM kill, SIGKILL, spot reclamation or a silent half-open TCP produce no observed
disconnect and so get no final flush — their loss window is the debounce interval at best. This is
the *at-most-once* guarantee stated plainly.

## Observability

Solara has no separate metrics system; state-persistence health is exposed on the existing
[`/resourcez`](/documentation/advanced/understanding/solara-server#live-resource-information)
endpoint under a `state` block (no backend I/O — it answers "is the feature on right now?"):

```json
"state": {
  "status": "healthy",              // off | healthy | degraded
  "circuit_breaker": "closed",      // closed | half_open | open
  "restore_attempts": 128,
  "restore_success": 120,
  "restore_bailout": 0,
  "restore_miss": 8,
  "restore_schema_reset": 0,
  "flush_ok": 4210,
  "flush_rejected": 0,
  "flush_failures": 0,
  "breaker_transitions": 0,
  "superseded_closes": 2,
  "superseded_while_connected": 0,
  "backend_last_ok_age_seconds": 0.4,
  "backend_last_error": null
}
```

The numbers that matter most: the **restore success ratio** after a rolling deploy is the number
that says the feature works; `superseded_while_connected` is the signature of broken stickiness,
cross-instance multi-tab, or an attack, and should be loud; `status` / `circuit_breaker` tell you
whether the feature quietly turned itself off.

`/readyz` is deliberately **backend-independent** — gating readiness on a recovery cache would turn
a Redis blip into a fleet-wide NotReady. Backend health appears only on `/resourcez`.

### Structured logs

The `solara.state` logger emits one greppable, alertable line per event:

```
restore  result=success|timeout|bailout|miss|fresh-schema kernel=… key=… cause=hmac|codec
flush    result=ok|rejected|error kernel=… n_fields=…
breaker  transition=open|half_open|closed reason=…
close    reason=page-close|cull|superseded|server-shutdown|evicted deleted=true|false
```

Alert on: a rising `restore result=bailout` rate, any `breaker transition=open`, and a rising rate
of `close reason=superseded`.

## Runbook

**"Users see refresh dialogs after a deploy."** Expected once *iff* the client bundle
(served JS/assets) changed — the browser genuinely needs the new assets. If the bundle did **not**
change, this is an incident:

1. Check `restore_bailout` on `/resourcez`. A spike means envelopes are failing verification/decode.
2. Check that **all replicas share the same `SOLARA_STATE_SECRET_KEYS`** — the #1 real cause. There
   is no automatic fleet-level check; verify by hand.
3. Check for `SOLARA_STATE_SCHEMA_TAG` stragglers (an instance on an old tag). A schema mismatch is
   a *graceful* reset (soft-remount, no dialog), so a dialog points at bailout or secrets, not the
   tag.

**"State is not restoring (fresh start, no dialog)."**

1. `/resourcez` `state` block first: `status` and `circuit_breaker`. `degraded` / `open` means the
   backend is unreachable and Solara has degraded to a stateless fresh start (see below).
2. Backend reachability from the instances (`redis-cli -u $SOLARA_STATE_URL ping`).
3. Secret-key uniformity across replicas.
4. Whether the affected variable actually had a stable explicit `key=` — a renamed or derived key
   resets state by design.

## Degraded mode

Redis is a recovery cache, not a database: **when it is down, Solara degrades to exactly today's
behavior.** A per-process circuit breaker opens after `SOLARA_STATE_BREAKER_FAILURES` consecutive
backend errors and stays open for `SOLARA_STATE_BREAKER_WINDOW` before a single half-open probe.
While open, connects skip the takeover read instantly (they do not each pay the connect timeout
during a brownout) and writes are skipped — so a Redis outage never taxes the interaction path.
Writes are off-thread, and keys stay dirty until acknowledged, so recovery is complete once the
backend returns. Every breaker transition is logged and counted.

See the [full configuration reference](/documentation/advanced/understanding/state-persistence#configuration-reference)
for all `SOLARA_STATE_*` settings.
