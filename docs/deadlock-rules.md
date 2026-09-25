# Deadlock rules for solara server

This document lists the locks in the solara server, the rules that keep them from forming a cycle, and how to test for and diagnose a hang.
Every rule below came from a real deadlock.
Read this before touching kernel lifecycle, reactive variables, or anything that runs on an event loop thread.

## The locks

| Lock | Where | Held for |
|------|-------|----------|
| `context.lock` (RLock) | `solara/server/server.py`, `app_loop` | the whole processing of one websocket message: the event handler, every render it triggers, every widget update it sends |
| reacton render lock (`_RenderContext.thread_lock`, non-reentrant) | reacton `core.py`, `render()` and `close()` | one full render pass, including the reconsolidation and effects phase |
| store lock (`KernelStore._lock`, `SharedStore._lock`, RLock) | `solara/toestand.py`, `solara/_stores.py` | one read-modify-write in `update()` or a field set, and the `_ensure_public_exists` read with mutation detection |
| init lock (`context.init_locks[key]`, RLock) | `KernelStore.get()` | the lazy `initial_value()` of one reactive in one kernel |
| `_listeners_lock` | `ValueBase` | taking a snapshot of the listeners, never while calling them |
| the keep-alive event loop | `solara/server/kernel_context.py` | shared by every kernel's cull timer in the process |
| the uvicorn event loop | `solara/server/starlette.py` | every `portal.call` from a kernel thread waits for it |

## Rule 1: never call `context.close()` on an event loop thread

In threaded mode the kernel's message thread holds `context.lock` for the whole event handler.
Each widget update in that handler is a `portal.call` that needs the uvicorn event loop to run.
`context.close()` blocks on `context.lock`.
Calling it from a coroutine therefore deadlocks whenever a handler is busy: the loop waits for the lock, the handler waits for the loop.

This was reproduced live for the HTTP evict route (permanent hang) and for the lifespan shutdown with uvicorn's `timeout_graceful_shutdown` (the loop is dead until the handler returns, so health checks fail).
Both now run the close off the loop, see `_off_loop` in `starlette.py`.
Off the loop, `close()` still waits for `context.lock`, so a busy handler delays the close for as long as it runs.
At shutdown that wait is bounded: `_close_all_contexts` closes every kernel in parallel under one deadline (`SOLARA_SERVER_SHUTDOWN_CLOSE_TIMEOUT`, default 10 seconds) and logs the kernels that did not make it.

The same rule holds for the keep-alive loop.
A cull used to run `close()` inline on it.
One kernel wedged in an event handler then blocked the cull of every other kernel in the process, which is a process-wide memory leak.
The cull now runs `close()` on its own thread (`_run_in_thread` in `kernel_context.py`) and only awaits the result.

## Rule 2: never fire listeners while holding a store lock

`update()` and field sets (`Ref(state.fields.x).value = ...`) take the store lock for their read-modify-write.
A listener runs arbitrary code, typically a render, which takes the render lock.
The render thread may set the same reactive from an effect, or with mutation detection on, even read it, which takes the store lock.
Firing under the lock is an ABBA deadlock between a background thread (a task writing progress) and the render thread.

The stores therefore split storing from firing: `_set_deferred()` stores under the lock and returns the `fire` call, and the caller runs it after releasing the lock.
`set()` still fires inline, because `set()` does not take the lock.
The price is ordering: two threads writing the same reactive at the same time may notify in the other order than they stored.
Plain `.value = x` never ordered its notifications either, and every listener solara installs (render, computed, persistence dirty-mark) re-reads the store.
A listener that must see the latest value reads it instead of using its argument.
The one solara listener that uses its argument is the external-change hook of the text inputs (`use_reactive` forwarding to `on_external_value_change` in `components/input.py`): two threads writing that reactive at the same time can leave the field showing the older text until the next render.
Any new store must implement `_set_deferred()` the same way.
`tests/unit/deadlock_test.py` pins this down with a deterministic two-thread cycle.

## Rule 3: never do blocking I/O under a lock

The state-persistence code (`solara/state`) does backend I/O.
It runs its final flush before `close()` takes `context.lock`, and the flush worker snapshots under the store lock but writes outside every lock.
`KernelStore.get()` holds an init lock while `initial_value()` runs, so an initial value that does I/O or takes another lock must not depend on anything that waits for this kernel.
The init lock logs every thread's stack after `SOLARA_STORAGE_INIT_LOCK_TIMEOUT` seconds instead of hanging silently.

## Rule 4: an `on_close` callback must not wait for the kernel to be closed

`closed_event` is set at the very end of `close()`.
A close callback (an `on_kernel_start` cleanup, a `use_effect` cleanup) that joins a thread waiting on `solara.kernel_closed_event()` waits for itself.
Signal such a thread with your own event, or let it poll `closed_event.is_set()` without joining it.

## Rule 5: the patched thread bootstrap must never raise before the thread is started

`patch.py` binds a new thread to its kernel context before `Thread._bootstrap` marks it as started.
An exception there kills the thread before `_started` is set, and the caller of `Thread.start()` waits forever.
The bootstrap therefore falls back to running without a context on any error, for example when the kernel closed between `Thread()` and `start()`.

## Rule 6: `close()` must always reach `closed_event.set()`

Everybody waiting on `closed_event` (tests, user threads, persistence) hangs if `close()` raises halfway.
Use tolerant operations in the close path (`dict.pop(key, None)`, not `del`), and catch and log per-step failures.
The close path also runs on plain threads (cull, evict, shutdown), which in non-threaded mode have no context id set: `get_current_thread_key` falls back to a thread key there instead of raising.

## Testing for deadlocks

Model the cycle with two threads and `threading.Event`s so the interleaving is deterministic.
Give each thread a `join(timeout)` and assert that no thread is alive afterwards.
Mark the test with `@pytest.mark.timeout`, so a hang becomes a failure with thread stacks.
See `tests/unit/deadlock_test.py` for the pattern.

For live reproduction, run the server with `PYTHONFAULTHANDLER=1`.
When it hangs, send `SIGABRT`: faulthandler dumps every thread's stack to stderr, which shows both sides of the cycle.
Drive the browser with playwright and keep an event handler busy (a loop with a `time.sleep` and a reactive write per iteration) while triggering the suspect path.

## Model checking (TLA+)

`docs/tla/` holds a PlusCal model of the lock table above (`SolaraLocks.tla`) and of the kernel lifecycle (`SolaraLifecycle.tla`), with a README on how to run TLC.
The lock model re-finds the three cycles under the old rules and passes under the new ones.
The lifecycle model found the cull-versus-reconnect race (a page marked connected on a kernel that is already closing) and validated the fix: mark the kernel as closing under the same `context.lock` hold as the decision (`_begin_close`).
Use the models as a design aid when adding a lock or a new close path, not as a CI gate: they are a hand transcription of the code and drift silently.

## Diagnosing a hang in production

Deploy with a way to get thread stacks without killing the process.
The cheapest is `faulthandler.register(signal.SIGUSR1, all_threads=True)` at startup, then `kill -USR1 <pid>`.
Do not use `SIGUSR1` under gunicorn, which reserves it for log reopening; pick `SIGUSR2`.
A blocked event loop shows as a failing `/readyz` while the process is alive.
