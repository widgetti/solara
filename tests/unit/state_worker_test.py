"""Tests for commit 2 of state persistence: the circuit breaker, the debounced write-behind
flush worker (incl. the bounded rejection protocol), the observability counters, and
watch-on-late-registration.

Deterministic by construction: the breaker uses an injected clock; the worker uses a tiny
debounce plus event/poll synchronization (never a long sleep). MemoryStateBackend + real
VirtualKernelContexts simulate two instances sharing one kernel's state, as in
state_persist_test.py.
"""

import time
import unittest.mock
from typing import Callable

import pytest

import solara
import solara.server.settings
import solara.server.kernel_context as kernel_context
from solara.server import kernel
from solara.state import CircuitBreaker, FlushOutcome, KernelFlushWorker, MemoryStateBackend, decode, session_hmac, stats
from solara.state import persist

SCHEMA_TAG = "schema-1"
SESSION_ID = "test-session"


@pytest.fixture(autouse=True)
def state_env(monkeypatch):
    monkeypatch.setattr(solara.server.settings.state, "secret_keys", "unit-test-secret-key")
    from solara.state import derive

    derive._reset_registry()
    persist._reset_registry()
    persist._attached_managers.clear()
    stats()._reset()
    yield
    derive._reset_registry()
    persist._reset_registry()
    persist._attached_managers.clear()
    stats()._reset()


class FakeClock:
    """A manually-advanced monotonic clock for deterministic breaker tests."""

    def __init__(self, t: float = 0.0) -> None:
        self.t = t

    def __call__(self) -> float:
        return self.t

    def advance(self, dt: float) -> None:
        self.t += dt


def make_context(id: str, session_id: str = SESSION_ID) -> kernel_context.VirtualKernelContext:
    return kernel_context.VirtualKernelContext(id=id, kernel=kernel.Kernel(), session_id=session_id)


def attach_manager(context, backend, *, generation=None, envelopes=None, restore_reason=None) -> persist.KernelStatePersistence:
    shmac = session_hmac(context.session_id)
    if generation is None:
        result = backend.takeover(context.id, shmac, SCHEMA_TAG)
        generation = result.generation
        if envelopes is None:
            envelopes = result.fields
        if restore_reason is None:
            restore_reason = result.reason
    return persist.attach(
        context,
        backend,
        session_hmac=shmac,
        schema_tag=SCHEMA_TAG,
        generation=generation,
        envelopes=envelopes or {},
        ttl=60.0,
        restore_reason=restore_reason,
    )


def wait_until(pred: Callable[[], bool], timeout: float = 2.0, interval: float = 0.005) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if pred():
            return True
        time.sleep(interval)
    return pred()


@pytest.fixture
def worker_factory():
    created = []

    def make(manager, **kw) -> KernelFlushWorker:
        kw.setdefault("breaker", CircuitBreaker(failures=3, window=30.0))
        kw.setdefault("has_connected_page", lambda: True)
        kw.setdefault("on_superseded", lambda: None)
        kw.setdefault("debounce", 0.02)
        worker = KernelFlushWorker(manager, **kw)
        created.append(worker)
        return worker

    yield make
    for worker in created:
        try:
            worker.stop()
            if worker._thread is not None:
                worker._thread.join(timeout=1.0)
        except Exception:  # noqa
            pass


# --- circuit breaker ----------------------------------------------------------------------


def test_breaker_opens_after_consecutive_failures():
    clock = FakeClock()
    breaker = CircuitBreaker(failures=3, window=30.0, clock=clock)
    assert breaker.state == "closed"
    assert breaker.allow()
    breaker.record_failure()
    breaker.record_failure()
    assert breaker.state == "closed"  # not yet at threshold
    breaker.record_failure()
    assert breaker.state == "open"
    assert not breaker.allow()  # open, window not elapsed
    assert stats().breaker_transitions == 1
    # a success while closed resets the run: three more failures are needed to re-open
    breaker2 = CircuitBreaker(failures=3, window=30.0, clock=clock)
    breaker2.record_failure()
    breaker2.record_failure()
    breaker2.record_success()
    breaker2.record_failure()
    breaker2.record_failure()
    assert breaker2.state == "closed"


def test_breaker_half_open_single_probe_success_closes():
    clock = FakeClock()
    breaker = CircuitBreaker(failures=1, window=30.0, clock=clock)
    breaker.record_failure()
    assert breaker.state == "open"
    assert not breaker.allow()  # window not elapsed yet
    clock.advance(30.0)
    assert breaker.allow()  # window elapsed -> a single probe is allowed
    assert breaker.state == "half_open"
    assert not breaker.allow()  # only ONE probe in flight
    breaker.record_success()
    assert breaker.state == "closed"
    assert breaker.allow()


def test_breaker_half_open_probe_failure_reopens():
    clock = FakeClock()
    breaker = CircuitBreaker(failures=1, window=30.0, clock=clock)
    breaker.record_failure()  # open
    clock.advance(30.0)
    assert breaker.allow()  # probe
    assert breaker.state == "half_open"
    breaker.record_failure()  # probe fails -> re-open, window restarts
    assert breaker.state == "open"
    assert not breaker.allow()  # window not elapsed since re-open
    clock.advance(30.0)
    assert breaker.allow()  # a fresh probe after the new window


# --- debounce -----------------------------------------------------------------------------


def test_debounce_coalesces_rapid_marks(worker_factory):
    r = solara.reactive(0, persist=True, key="test.worker.debounce")
    backend = MemoryStateBackend()
    context = make_context("debounce-kernel")
    manager = attach_manager(context, backend)
    worker = worker_factory(manager, debounce=0.03)
    worker.start()
    with context:
        for i in range(5):
            r.value = i
    # a burst of marks collapses to exactly one flush attempt
    assert worker.wait_for_flushes(1)
    time.sleep(0.03)  # give any (erroneous) extra flush time to register
    assert worker.flush_attempts == 1
    assert manager.dirty_keys == set()
    assert backend.peek_generation(context.id) == 1


# --- breaker gating (no stranding) --------------------------------------------------------


def test_breaker_open_leaves_keys_dirty_then_drains(worker_factory):
    key = "test.worker.strand"
    r = solara.reactive(0, persist=True, key=key)
    backend = MemoryStateBackend()
    context = make_context("strand-kernel")
    manager = attach_manager(context, backend)
    clock = FakeClock()
    breaker = CircuitBreaker(failures=1, window=30.0, clock=clock)
    breaker.record_failure()  # open
    assert breaker.state == "open"
    worker = worker_factory(manager, breaker=breaker, debounce=0.02)
    worker.start()
    with context:
        r.value = 5
    # first attempt hits an open breaker: skip, keys stay dirty, nothing written
    assert worker.wait_for_flushes(1)
    assert manager.dirty_keys == {key}
    assert backend.peek_generation(context.id) is None
    # let the window elapse; the re-armed timer retries and, with the breaker now closing on a
    # successful probe, drains the dirty keys (no permanent stranding)
    clock.advance(30.0)
    # wait on the backend observable: flush_now drains dirty BEFORE the write lands
    assert wait_until(lambda: backend.peek_generation(context.id) == 1)
    assert manager.dirty_keys == set()
    assert breaker.state == "closed"


# --- rejection protocol (§5.5) ------------------------------------------------------------


def test_rejection_connected_retakes_once(worker_factory):
    key = "test.worker.retake"
    r = solara.reactive("v0", persist=True, key=key)
    field = persist.FIELD_PREFIX + key
    backend = MemoryStateBackend()
    kernel_id = "retake-kernel"
    shmac = session_hmac(SESSION_ID)

    context = make_context(kernel_id)
    manager = attach_manager(context, backend)  # generation 1 (miss)
    with context:
        r.value = "from-A"
    assert manager.flush_now() == FlushOutcome.OK  # generation 1 stored
    # another instance takes over -> generation 2, fencing A out
    assert backend.takeover(kernel_id, shmac, SCHEMA_TAG).generation == 2

    worker = worker_factory(manager, has_connected_page=lambda: True, debounce=0.02)
    worker.start()
    with context:
        r.value = "from-A-again"
    # A's flush is fenced (gen 1 != 2) -> exactly one re-takeover to gen 3, then re-flush
    assert wait_until(lambda: manager.generation == 3 and backend.peek_generation(kernel_id) == 3)
    assert wait_until(lambda: manager.dirty_keys == set())
    assert worker.retakeovers_this_epoch == 1
    assert not manager.disabled
    # the new generation's data is A's latest in-memory value (the takeover read was discarded)
    result = backend.takeover(kernel_id, shmac, SCHEMA_TAG)
    assert decode(result.fields[field], kernel_id=kernel_id, field_name=field) == "from-A-again"


def test_second_rejection_same_epoch_concedes(worker_factory):
    key = "test.worker.concede"
    r = solara.reactive(0, persist=True, key=key)
    backend = MemoryStateBackend()
    context = make_context("concede-kernel")
    manager = attach_manager(context, backend)
    superseded = []
    # high threshold so a REJECT (healthy backend) never opens the breaker
    breaker = CircuitBreaker(failures=100, window=30.0)
    worker = worker_factory(
        manager,
        breaker=breaker,
        has_connected_page=lambda: True,
        on_superseded=lambda: superseded.append(1),
        debounce=0.02,
    )
    worker.start()
    with unittest.mock.patch.object(backend, "flush", return_value=False):
        with context:
            r.value = 1
        # reject -> re-take -> reject again within the epoch -> concede
        assert wait_until(lambda: manager.disabled)
    assert worker.retakeovers_this_epoch == 1
    assert stats().superseded_while_connected == 1
    assert superseded == []  # concede does not close the context / call on_superseded
    assert wait_until(lambda: worker._thread is not None and not worker._thread.is_alive())
    # the live session keeps working; persistence is simply off now
    with context:
        r.value = 2
        assert r.value == 2
    assert manager.flush_now() == FlushOutcome.DISABLED


def test_rejection_no_connected_page_supersedes(worker_factory):
    key = "test.worker.orphan"
    r = solara.reactive(0, persist=True, key=key)
    backend = MemoryStateBackend()
    context = make_context("orphan-kernel")
    manager = attach_manager(context, backend)
    superseded = []
    breaker = CircuitBreaker(failures=100, window=30.0)
    worker = worker_factory(
        manager,
        breaker=breaker,
        has_connected_page=lambda: False,
        on_superseded=lambda: superseded.append(1),
        debounce=0.02,
    )
    worker.start()
    with unittest.mock.patch.object(backend, "flush", return_value=False):
        with context:
            r.value = 1
        assert wait_until(lambda: superseded == [1])
    assert stats().superseded_closes == 1
    assert worker.retakeovers_this_epoch == 0  # orphan does not reclaim
    assert wait_until(lambda: worker._thread is not None and not worker._thread.is_alive())


def test_new_epoch_resets_retakeover_budget(worker_factory):
    key = "test.worker.epoch"
    r = solara.reactive("v", persist=True, key=key)
    backend = MemoryStateBackend()
    kernel_id = "epoch-kernel"
    shmac = session_hmac(SESSION_ID)
    context = make_context(kernel_id)
    manager = attach_manager(context, backend)  # gen 1
    breaker = CircuitBreaker(failures=100, window=30.0)
    worker = worker_factory(manager, breaker=breaker, has_connected_page=lambda: True, debounce=0.02)
    worker.start()

    with context:
        r.value = "a"
    # confirm the gen-1 flush LANDED before bumping the generation below - an in-flight flush
    # would get fenced and spend the retake budget on the wrong write (dirty empties before
    # the backend write completes)
    assert wait_until(lambda: backend.peek_generation(kernel_id) == 1 and manager.dirty_keys == set())
    # someone takes over -> gen 2; A re-takes once (gen 3)
    backend.takeover(kernel_id, shmac, SCHEMA_TAG)
    with context:
        r.value = "b"
    assert wait_until(lambda: manager.generation == 3 and backend.peek_generation(kernel_id) == 3 and manager.dirty_keys == set())
    assert worker.retakeovers_this_epoch == 1

    # a genuine reconnect starts a new epoch and restores the budget
    worker.new_epoch()
    assert worker.retakeovers_this_epoch == 0
    backend.takeover(kernel_id, shmac, SCHEMA_TAG)  # gen 4
    with context:
        r.value = "c"
    assert wait_until(lambda: manager.generation == 5 and backend.peek_generation(kernel_id) == 5 and manager.dirty_keys == set())
    assert worker.retakeovers_this_epoch == 1
    assert not manager.disabled


# --- close --------------------------------------------------------------------------------


def test_close_flushes_pending_dirty_keys(worker_factory):
    key = "test.worker.close"
    r = solara.reactive(0, persist=True, key=key)
    backend = MemoryStateBackend()
    context = make_context("close-kernel")
    manager = attach_manager(context, backend)
    # a large debounce so the background thread will NOT flush on its own before close()
    worker = worker_factory(manager, debounce=100.0)
    worker.start()
    with context:
        r.value = 7
    assert manager.dirty_keys == {key}
    worker.close(timeout=2.0)
    # close did the bounded final flush and detached the manager
    assert manager.dirty_keys == set()
    assert backend.peek_generation(context.id) == 1
    assert worker._thread is not None and not worker._thread.is_alive()
    assert context.state_persistence is None


# --- observability ------------------------------------------------------------------------


def test_stats_counters_and_as_dict():
    key = "test.worker.stats"
    r = solara.reactive(0, persist=True, key=key)
    backend = MemoryStateBackend()
    context = make_context("stats-kernel")
    manager = attach_manager(context, backend, restore_reason="miss")
    assert stats().restore_attempts == 1
    assert stats().restore_miss == 1

    with context:
        r.value = 3
    assert manager.flush_now() == FlushOutcome.OK
    assert stats().flush_ok == 1

    d = stats().as_dict()
    assert d["restore_attempts"] == 1
    assert d["restore_miss"] == 1
    assert d["flush_ok"] == 1
    assert d["backend_last_error"] is None
    assert d["backend_last_ok_age_seconds"] is not None and d["backend_last_ok_age_seconds"] >= 0.0

    with unittest.mock.patch.object(backend, "flush", return_value=False):
        with context:
            r.value = 4
        assert manager.flush_now() == FlushOutcome.REJECTED
    assert stats().flush_rejected == 1

    with unittest.mock.patch.object(backend, "flush", side_effect=RuntimeError("down")):
        with context:
            r.value = 5
        assert manager.flush_now() == FlushOutcome.ERROR
    assert stats().flush_failures == 1
    assert stats().as_dict()["backend_last_error"] is not None


# --- watch-on-late-registration -----------------------------------------------------------


def test_late_registered_reactive_is_watched_by_attached_manager():
    backend = MemoryStateBackend()
    context = make_context("late-kernel")
    manager = attach_manager(context, backend)  # no persisted reactives exist yet
    # a persisted reactive imported AFTER the manager attached must still be dirty-tracked
    key = "test.worker.late"
    r = solara.reactive(0, persist=True, key=key)
    with context:
        r.value = 9
    assert manager.dirty_keys == {key}
    assert manager.flush_now() == FlushOutcome.OK
    assert backend.peek_generation(context.id) == 1
