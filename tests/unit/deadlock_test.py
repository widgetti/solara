"""Regression tests for lock-ordering deadlocks.

Every test here models a real lock cycle with two threads and events, so the
interleaving is deterministic: no sleeps, no luck. A failing test hangs, which
pytest-timeout turns into a failure with the thread stacks.
"""

import asyncio
import logging
import threading
import time

import pytest

import solara
import solara.server.app  # installs the Thread patch
from solara.server import kernel_context
import solara.server.starlette as starlette_server
from solara.toestand import Ref

DEADLOCK_TIMEOUT = 5.0


def _cross_locks(state, set_a, set_b):
    """The reactive/render lock cycle.

    Thread 1 sets a reactive: the store's lock is taken for the read-modify-write
    and the listeners fire. The listener needs another lock (in solara this is
    reacton's render lock, held for a whole render pass, effects included).

    Thread 2 holds that other lock (it is "rendering") and sets the same
    reactive, which needs the store's lock.

    Firing listeners while holding the store's lock makes this an ABBA deadlock;
    firing after releasing the lock does not.
    """
    # reacton's render lock is re-entered by the render thread's own listeners (it checks
    # _is_rendering before rendering again), so model it with an RLock
    render_lock = threading.RLock()
    render_lock_held = threading.Event()
    listener_entered = threading.Event()
    listener_finished = threading.Event()

    def listener(*_ignore):
        listener_entered.set()
        with render_lock:
            pass
        listener_finished.set()

    def thread1():
        assert render_lock_held.wait(DEADLOCK_TIMEOUT)
        set_a()

    def thread2():
        with render_lock:
            render_lock_held.set()
            assert listener_entered.wait(DEADLOCK_TIMEOUT)
            set_b()

    unsubscribe = state.subscribe_change(listener)
    try:
        threads = [threading.Thread(target=thread1, daemon=True), threading.Thread(target=thread2, daemon=True)]
        for thread in threads:
            thread.start()
        deadline = time.monotonic() + DEADLOCK_TIMEOUT
        for thread in threads:
            thread.join(max(0.0, deadline - time.monotonic()))
        stuck = [thread for thread in threads if thread.is_alive()]
        assert not stuck, "deadlock: listeners fired while the store lock was held"
        assert listener_finished.is_set()
    finally:
        unsubscribe()


@pytest.mark.timeout(30)
def test_field_set_does_not_fire_listeners_under_the_store_lock():
    state = solara.reactive({"a": 0, "b": 0})
    a = Ref(state.fields["a"])
    b = Ref(state.fields["b"])

    def set_a():
        a.value = 1

    def set_b():
        b.value = 2

    _cross_locks(state, set_a, set_b)
    assert state.value == {"a": 1, "b": 2}


@pytest.mark.timeout(30)
def test_update_does_not_fire_listeners_under_the_store_lock():
    state = solara.reactive({"a": 0, "b": 0})
    _cross_locks(state, lambda: state.update(a=1), lambda: state.update(b=2))
    assert state.value == {"a": 1, "b": 2}


@pytest.mark.timeout(30)
def test_nested_field_set_does_not_fire_listeners_under_the_store_lock():
    state = solara.reactive({"outer": {"a": 0, "b": 0}})
    a = Ref(state.fields["outer"]["a"])
    b = Ref(state.fields["outer"]["b"])

    def set_a():
        a.value = 1

    def set_b():
        b.value = 2

    _cross_locks(state, set_a, set_b)
    assert state.value == {"outer": {"a": 1, "b": 2}}


@pytest.mark.timeout(30)
def test_update_is_still_atomic_across_threads():
    # firing outside the lock must not cost the read-modify-write atomicity of update()
    counter = solara.reactive({"n": 0})
    n_threads = 8
    n_updates = 200

    def worker():
        for _ in range(n_updates):
            counter.update(lambda value: {"n": value["n"] + 1})

    threads = [threading.Thread(target=worker, daemon=True) for _ in range(n_threads)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(DEADLOCK_TIMEOUT)
    assert counter.value == {"n": n_threads * n_updates}


@pytest.mark.timeout(30)
def test_field_set_is_still_atomic_across_threads():
    state = solara.reactive({"inner": {"n": 0}})
    inner = Ref(state.fields["inner"])
    n_threads = 8
    n_updates = 200

    def worker():
        for _ in range(n_updates):
            inner.update(lambda value: {"n": value["n"] + 1})

    threads = [threading.Thread(target=worker, daemon=True) for _ in range(n_threads)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(DEADLOCK_TIMEOUT)
    assert state.value == {"inner": {"n": n_threads * n_updates}}


@pytest.mark.timeout(30)
def test_thread_start_does_not_hang_when_kernel_closes_before_bootstrap():
    """The patched Thread bootstrap runs before Thread.start() returns.

    If it raises (the kernel closed between Thread() and start(): the shell is
    gone), the thread dies before setting the started flag and start() waits
    forever. The bootstrap must fall back to running without a kernel context.
    """
    context = kernel_context.create_dummy_context()
    with context:
        thread = threading.Thread(target=lambda: None, daemon=True)
    assert thread.current_context is context  # type: ignore
    # the close tore down the kernel's shell, but did not set kernel=None yet
    shell = context.kernel.shell
    context.kernel.shell = None  # type: ignore

    starter_done = threading.Event()

    def start_it():
        thread.start()
        thread.join(DEADLOCK_TIMEOUT)
        starter_done.set()

    starter = threading.Thread(target=start_it, daemon=True)
    starter.start()
    try:
        assert starter_done.wait(DEADLOCK_TIMEOUT), "Thread.start() hung: the patched bootstrap raised before the thread was marked started"
    finally:
        context.kernel.shell = shell
        context.close()


class _RacyDict(dict):
    """A current_context whose items() snapshot is followed by a concurrent pop."""

    def __init__(self, source, key):
        super().__init__(source)
        self._key = key

    def items(self):
        items = list(super().items())
        self.pop(self._key, None)
        return items


@pytest.mark.timeout(30)
def test_close_tolerates_thread_key_removed_concurrently(monkeypatch):
    # _finish_close scans current_context for entries pointing at itself and removes them;
    # a thread exiting at the same moment pops its own key. That must not abort the close:
    # an aborted close never sets closed_event, and everybody waiting on it hangs.
    context = kernel_context.create_dummy_context()
    key = "some-thread-that-is-exiting"
    racy = _RacyDict(kernel_context.current_context, key)
    racy[key] = context
    monkeypatch.setattr(kernel_context, "current_context", racy)
    context.close()
    assert context.closed_event.is_set()
    assert key not in racy


@pytest.mark.timeout(30)
def test_run_in_thread_delivers_result_and_exception():
    loop = asyncio.new_event_loop()
    try:
        assert loop.run_until_complete(kernel_context._run_in_thread(lambda: 42, name="t")) == 42

        def boom():
            raise ValueError("boom")

        with pytest.raises(ValueError, match="boom"):
            loop.run_until_complete(kernel_context._run_in_thread(boom, name="t"))
    finally:
        loop.close()


@pytest.mark.timeout(30)
def test_cull_resolves_disconnect_future_when_close_raises(monkeypatch):
    # the caller of page_disconnect awaits the returned future; a close() that raises
    # inside the cull must not leave it pending forever
    monkeypatch.setattr(kernel_context.solara.server.settings.kernel, "cull_timeout", "0s")
    context = kernel_context.create_dummy_context()
    kernel_context.contexts[context.id] = context
    real_close = context.close

    def failing_close(reason="unknown"):
        real_close(reason=reason)
        raise RuntimeError("close failed")

    monkeypatch.setattr(context, "close", failing_close)
    loop = asyncio.new_event_loop()
    try:

        async def run():
            context.page_connect("page")
            future = context.page_disconnect("page")
            await asyncio.wait_for(future, DEADLOCK_TIMEOUT)

        loop.run_until_complete(run())
    finally:
        loop.close()
    assert context.closed_event.is_set()


@pytest.mark.timeout(30)
def test_shutdown_close_is_bounded_by_the_deadline(caplog, monkeypatch):
    # one kernel is stuck in an event handler (its lock is held); the other must still
    # close, and the shutdown must return at the deadline, not when the handler ends
    stuck = kernel_context.create_dummy_context()
    stuck.id = "stuck"
    free = kernel_context.create_dummy_context()
    free.id = "free"
    monkeypatch.setattr(kernel_context, "contexts", {"stuck": stuck, "free": free})
    release = threading.Event()
    acquired = threading.Event()

    def handler():
        with stuck.lock:
            acquired.set()
            release.wait(DEADLOCK_TIMEOUT * 2)

    holder = threading.Thread(target=handler, daemon=True)
    holder.start()
    assert acquired.wait(DEADLOCK_TIMEOUT)
    t0 = time.monotonic()
    with caplog.at_level(logging.WARNING, logger="solara.server.fastapi"):
        starlette_server._close_all_contexts(deadline_seconds=1.0)
    elapsed = time.monotonic() - t0
    try:
        assert elapsed < DEADLOCK_TIMEOUT, "shutdown waited for the stuck handler"
        assert free.closed_event.is_set()
        assert not stuck.closed_event.is_set()
        assert any("stuck" in record.getMessage() and "deadline" in record.getMessage() for record in caplog.records)
    finally:
        release.set()
        holder.join(DEADLOCK_TIMEOUT)
        assert stuck.closed_event.wait(DEADLOCK_TIMEOUT)


@pytest.mark.timeout(30)
def test_close_from_a_plain_thread_in_non_threaded_mode(monkeypatch):
    # cull, evict and shutdown close kernels from plain threads. In non-threaded mode the
    # context key comes from a ContextVar that such a thread never set; close() must still
    # run to completion (and set closed_event) there.
    monkeypatch.setattr(kernel_context.solara.server.settings.kernel, "threaded", False)
    contexts = [kernel_context.create_dummy_context() for _ in range(2)]
    for index, context in enumerate(contexts):
        context.id = f"non-threaded-{index}"
        kernel_context.contexts[context.id] = context
    errors = []

    def close(context):
        try:
            context.close(reason="evicted")
        except BaseException as error:  # noqa
            errors.append(error)

    threads = [threading.Thread(target=close, args=(context,), daemon=True) for context in contexts]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(DEADLOCK_TIMEOUT)
    assert not errors
    for context in contexts:
        assert context.closed_event.is_set()
        assert context.id not in kernel_context.contexts
        assert context not in kernel_context.current_context.values()
