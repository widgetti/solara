# State-persistence cross-instance failover demo

A self-contained demo of Solara's opt-in reactive **state persistence**: when a websocket
reconnect lands on a *different* server instance (a load-balancer failover, a pod crash, a
rolling deploy), the app **soft-remounts** with your opted-in state restored — no refresh
dialog, no page reload.

It runs two Solara backends behind a [Caddy](https://caddyserver.com/) `round_robin` load
balancer, both sharing one Redis. Caddy assigns each new connection to a backend in turn, so a
reconnect after a disconnect lands on the *other* backend — a real cross-instance failover.

## What it demonstrates

The app ([`app.py`](./app.py)) has:

- **Two persisted inputs** — a text filter and a slider (`persist=True`, each with an explicit
  `key=`). These **survive** the failover: they are restored from Redis before the first render
  on the new instance.
- **A derived "expensive" task** (`solara.lab.use_task`) keyed on those inputs. It is **not**
  persisted — on the new instance it simply **recomputes** from the restored inputs, exactly as
  on a cold start. This is the core discipline: **persist inputs, recompute outputs.**
- **A non-persisted scratch note** (`use_state`). It **resets** on failover — the honest
  recovery model: only opted-in state comes back.
- **The fencing epoch** (`solara.state_generation()`), which **increases by one** on every
  failover.
- **A "Disconnect websocket" button** that closes the server-side socket (the pattern from
  `tests/integration/reconnect_test.py`), forcing the reconnect that round-robins to the other
  backend.

## Try it: what to click, what you should see

1. Change the **filter** and move the **slider**. Type something in the **scratch note**.
2. Trigger a failover, either:
   - click **Disconnect websocket**, or
   - open the browser devtools console and run `solara.debug.simulateFailover()`.
3. Observe, after a brief "Restoring session…":
   - the filter and slider are **back to your values** (restored),
   - the "expensive" result **recomputes** from them,
   - the scratch note is **empty again** (reset — it was never persisted),
   - the fencing epoch has **incremented**,
   - **no** "Please refresh the page" dialog appears.

`solara.debug.simulateFailover()` also works in a **single** `solara run` process with the
memory backend (`SOLARA_STATE_BACKEND=memory`, `SOLARA_STATE_SECRET_KEYS=anything`) — no
infrastructure needed. Make it a habit: walk each page of your app, trigger a failover at each
interesting state, and verify what you see.

## Run it

### Option A — Docker Compose (redis + two backends + caddy)

```bash
docker compose up
# open http://localhost:8000
```

See [`docker-compose.yml`](./docker-compose.yml).

### Option B — locally, no Docker

Prerequisites:

- **Redis** running locally: `redis-server --maxmemory-policy noeviction`
- **Caddy 2**: https://caddyserver.com/docs/install
- **Solara with the redis extra**: `pip install 'solara[redis]'`

Then:

```bash
./run.sh
# open http://localhost:8000
```

See [`run.sh`](./run.sh) and [`Caddyfile`](./Caddyfile).

## Configuration notes

- **Both backends must share the same `SOLARA_STATE_SECRET_KEYS`.** State envelopes are
  HMAC-signed; a mismatch across replicas is the #1 real-world cause of silent restore failures.
  The demo uses a throwaway secret — change it for anything real.
- **Redis is a recovery cache, not a database.** Use `noeviction` + TTLs and alert on memory;
  never point this at a shared `allkeys-lru` cache instance (a memory spike would silently drop
  live sessions).
- **Sticky sessions stay the fast path.** This feature is the recovery layer for what stickiness
  cannot cover (crash, scale-in, spot reclamation, deploys outliving the drain window). Single
  instance deployments should not enable it.

## Learn more

- Understanding state persistence:
  https://solara.dev/documentation/advanced/understanding/state-persistence
- Deploying with state persistence:
  https://solara.dev/documentation/getting_started/deploying/state-persistence
