"""Tests for commit 2 of state persistence: the SERVER wiring.

The memory backend plus the dev/test kernel-eviction primitive gives a full single-process
failover simulation (design §6.4): restore-for-real without Redis. Covered here: the takeover
on connect (miss/restore/identity-mismatch/timeout/breaker-open), the reuse-branch ownership
check (A -> B -> A double reconnect), the reason-gated fenced delete, the orphan-cull knob, the
/resourcez state block, the fail-closed eviction route, and the public API
(solara.kernel_closed_event / solara.state_generation).

Deterministic: a tiny flush debounce plus event/poll synchronization (never long sleeps), real
VirtualKernelContexts + MemoryStateBackend, as in state_persist_test.py / state_worker_test.py.
"""

import asyncio
import json
import time
from typing import Callable
from unittest.mock import Mock

import pytest

import solara
import solara.server.settings
import solara.server.kernel_context as kc
import solara.state
from solara.server import kernel
from solara.state import FlushOutcome, MemoryStateBackend, encode, persist, session_hmac, stats

SCHEMA_TAG = "server-schema-1"


@pytest.fixture(autouse=True)
def state_env(monkeypatch):
    from solara.state import derive

    monkeypatch.setattr(solara.server.settings.state, "secret_keys", "unit-test-secret-key")
    monkeypatch.setattr(solara.server.settings.state, "schema_tag", SCHEMA_TAG)
    monkeypatch.setattr(solara.server.settings.state, "flush_debounce", "10ms")
    derive._reset_registry()
    persist._reset_registry()
    persist._attached_managers.clear()
    stats()._reset()
    solara.state.reset_breaker()
    yield
    # close any contexts a test left open (stops worker threads); then reset everything
    for context in list(kc.contexts.values()):
        try:
            context.close()
        except Exception:  # noqa
            pass
    kc.contexts.clear()
    derive._reset_registry()
    persist._reset_registry()
    persist._attached_managers.clear()
    stats()._reset()
    solara.state.reset_breaker()
    solara.state.reset_backend()


@pytest.fixture
def backend(monkeypatch) -> MemoryStateBackend:
    """A shared-in-process MemoryStateBackend wired in via get_backend (as the server reads it)."""
    be = MemoryStateBackend()
    monkeypatch.setattr(solara.state, "get_backend", lambda: be)
    return be


def wait_until(pred: Callable[[], bool], timeout: float = 2.0, interval: float = 0.005) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if pred():
            return True
        time.sleep(interval)
    return pred()


def field_of(key: str) -> str:
    return persist.FIELD_PREFIX + key


# --- the marquee test: full single-process failover loop ----------------------------------


def test_single_process_failover_loop(backend):
    r = solara.reactive("start", persist=True, key="test.server.failover")
    session_id, kernel_id = "sess-failover", "kern-failover"

    context = kc.initialize_virtual_kernel(session_id, kernel_id, Mock())
    context.page_connect("page-1")
    assert context.state_persistence is not None
    assert context.state_flush_worker is not None

    with context:
        r.value = "restored-value"
    # the debounced worker flushes it to the backend
    # wait on the backend observable: flush_now drains the dirty set BEFORE the write,
    # so waiting on not-dirty would race the backend I/O
    assert wait_until(lambda: backend.peek_generation(kernel_id) == 1)

    # evict (the server half of simulateFailover): flush-and-leave + remove the in-memory context
    context.close(reason="evicted")
    assert context.close_reason == "evicted"
    assert kernel_id not in kc.contexts
    assert backend.peek_generation(kernel_id) == 1  # the hash survived (no delete on evict)

    # reconnect lands on a fresh context; restore runs for real from the surviving hash
    context2 = kc.initialize_virtual_kernel(session_id, kernel_id, Mock())
    assert context2 is not context
    assert context2.state_persistence is not None
    with context2:
        assert r.value == "restored-value"  # restored at first read


# --- A -> B -> A double reconnect (reuse-branch ownership check, §5.1) ---------------------


def test_double_reconnect_supersedes_stale_context(backend):
    r = solara.reactive("v0", persist=True, key="test.server.abab")
    session_id, kernel_id = "sess-abab", "kern-abab"
    shmac = session_hmac(session_id)

    # instance A lives in contexts and flushes "from-A" at generation 1
    context_a = kc.initialize_virtual_kernel(session_id, kernel_id, Mock())
    context_a.page_connect("pageA")
    with context_a:
        r.value = "from-A"
    assert wait_until(lambda: backend.peek_generation(kernel_id) == 1)

    # simulate instance B taking over on another instance: takeover bumps to 2, then flush "from-B"
    result_b = backend.takeover(kernel_id, shmac, SCHEMA_TAG)
    assert result_b.generation == 2
    context_b = kc.VirtualKernelContext(id=kernel_id, kernel=kernel.Kernel(), session_id=session_id)
    manager_b = solara.state.attach(context_b, backend, session_hmac=shmac, schema_tag=SCHEMA_TAG, generation=result_b.generation, envelopes=result_b.fields)
    with context_b:
        r.value = "from-B"
    assert manager_b.flush_now() == FlushOutcome.OK
    assert backend.peek_generation(kernel_id) == 2

    # reconnect lands on the reuse branch (context A still live): must detect the mismatch, close A
    # as superseded, create a fresh context, and restore B's latest value
    context_new = kc.initialize_virtual_kernel(session_id, kernel_id, Mock())
    assert context_new is not context_a
    assert context_a.closed_event.is_set()
    assert context_a.close_reason == "superseded"
    assert context_new.state_persistence is not None
    with context_new:
        assert r.value == "from-B"


# --- session mismatch on takeover ---------------------------------------------------------


def test_session_mismatch_no_restore(backend):
    r = solara.reactive("default", persist=True, key="test.server.mismatch")
    kernel_id = "kern-mismatch"
    # the legitimate owner (a different session) wrote a hash
    owner_hmac = session_hmac("owner-session")
    field = field_of("test.server.mismatch")
    fields = {field: encode("owner-secret", kernel_id=kernel_id, field_name=field)}
    assert backend.flush(kernel_id, 1, fields, 60.0, owner_hmac, SCHEMA_TAG)

    # an attacker connects with the same kernel id but a different session
    context = kc.initialize_virtual_kernel("attacker-session", kernel_id, Mock())
    assert context.state_persistence is None  # identity mismatch -> not attached, no write rights
    assert context.state_flush_worker is None
    with context:
        assert r.value == "default"  # never the owner's value
        assert solara.state_generation() is None


# --- restore timeout -> unpersisted + late claim-or-delete --------------------------------


def test_restore_timeout_degrades_and_late_deletes(backend, monkeypatch):
    solara.reactive("x", persist=True, key="test.server.timeout")
    session_id, kernel_id = "sess-timeout", "kern-timeout"
    shmac = session_hmac(session_id)
    field = field_of("test.server.timeout")
    # a hash exists, so the late takeover returns "restored" and the claim-or-delete removes it
    assert backend.flush(kernel_id, 1, {field: encode("v", kernel_id=kernel_id, field_name=field)}, 60.0, shmac, SCHEMA_TAG)

    monkeypatch.setattr(solara.server.settings.state, "connect_timeout", 0.05)
    real_takeover = backend.takeover

    def slow_takeover(*args, **kwargs):
        time.sleep(0.3)  # > connect_timeout, so the connect path gives up and degrades
        return real_takeover(*args, **kwargs)

    monkeypatch.setattr(backend, "takeover", slow_takeover)

    context = kc.initialize_virtual_kernel(session_id, kernel_id, Mock())
    # degrade-to-today: the kernel runs unpersisted
    assert context.state_persistence is None
    assert context.state_flush_worker is None
    # the late takeover eventually completes and its result fenced-deletes the stale hash (§5.1)
    assert wait_until(lambda: backend.peek_generation(kernel_id) is None)


# --- breaker open -> connect skips takeover instantly -------------------------------------


def test_breaker_open_skips_takeover(backend, monkeypatch):
    solara.reactive("x", persist=True, key="test.server.breakeropen")
    breaker = solara.state.get_breaker()
    for _ in range(solara.server.settings.state.breaker_failures):
        breaker.record_failure()
    assert breaker.state == "open"

    called = []
    monkeypatch.setattr(backend, "takeover", lambda *a, **k: called.append(1))

    t0 = time.monotonic()
    context = kc.initialize_virtual_kernel("sess-b", "kern-breakeropen", Mock())
    elapsed = time.monotonic() - t0

    assert elapsed < 0.2  # instant: no takeover deadline paid during the brownout
    assert called == []  # the takeover read was skipped entirely
    assert context.state_persistence is None


# --- reason-gated fenced delete (§5.4) ----------------------------------------------------


def _connect_flush(backend, key, value, session_id, kernel_id):
    r = solara.reactive("init", persist=True, key=key)
    context = kc.initialize_virtual_kernel(session_id, kernel_id, Mock())
    context.page_connect("p1")
    with context:
        r.value = value
    # wait on the backend observable: flush_now drains the dirty set BEFORE the write,
    # so waiting on not-dirty would race the backend I/O
    assert wait_until(lambda: backend.peek_generation(kernel_id) == 1)
    return context


def test_page_close_deletes_hash(backend):
    context = _connect_flush(backend, "test.server.pageclose", 5, "sess-pc", "kern-pc")
    context.page_close("p1")  # a genuine tab close -> close(reason="page-close") -> fenced delete
    assert context.close_reason == "page-close"
    assert backend.peek_generation("kern-pc") is None


@pytest.mark.parametrize("reason", ["cull", "evicted", "server-shutdown"])
def test_non_page_close_keeps_hash(backend, reason):
    context = _connect_flush(backend, f"test.server.keep.{reason}", 9, f"sess-{reason}", f"kern-{reason}")
    context.close(reason=reason)  # flush-and-leave-for-TTL: no delete
    assert context.close_reason == reason
    assert backend.peek_generation(f"kern-{reason}") == 1


# --- orphan cull knob (shared backend only, §5.4) -----------------------------------------


def test_orphan_cull_timeout_selection(monkeypatch):
    class SharedBackend(MemoryStateBackend):
        shared = True

    shared = SharedBackend()
    monkeypatch.setattr(solara.state, "get_backend", lambda: shared)
    monkeypatch.setattr(solara.server.settings.state, "orphan_cull_timeout", "5m")
    monkeypatch.setattr(solara.server.settings.kernel, "cull_timeout", "24h")
    solara.reactive(0, persist=True, key="test.server.orphan")

    context = kc.initialize_virtual_kernel("sess-orphan", "kern-orphan", Mock())
    assert context.state_persistence is not None
    # shared backend + attached, enabled manager -> the shortened orphan cull
    assert context._cull_timeout_seconds() == solara.util.parse_timedelta("5m")

    # no persistence -> today's long cull_timeout (state and kernel die together for memory)
    plain = kc.VirtualKernelContext(id="kern-plain", kernel=kernel.Kernel(), session_id="s")
    assert plain._cull_timeout_seconds() == solara.util.parse_timedelta("24h")


def test_orphan_cull_not_shortened_for_memory_backend(backend):
    # the default fixture backend has shared=False (memory): keep today's cull_timeout
    solara.reactive(0, persist=True, key="test.server.orphan.memory")
    context = kc.initialize_virtual_kernel("sess-om", "kern-om", Mock())
    assert context.state_persistence is not None
    assert context._cull_timeout_seconds() == solara.util.parse_timedelta(solara.server.settings.kernel.cull_timeout)


# --- /resourcez state block (§7a) ---------------------------------------------------------


def _call_resourcez(auth=None):
    from solara.server.starlette import resourcez

    request = Mock()
    request.query_params.get.return_value = None  # not verbose
    request.headers = {"authorization": auth} if auth else {}
    response = asyncio.run(resourcez(request))
    return json.loads(response.body)


def test_resourcez_state_block_healthy(backend):
    data = _call_resourcez()
    assert "state" in data
    assert data["state"]["status"] == "healthy"
    assert data["state"]["circuit_breaker"] == "closed"
    # the §7a counters are present
    assert "restore_attempts" in data["state"]
    assert "flush_ok" in data["state"]


def test_resourcez_state_block_off(monkeypatch):
    monkeypatch.setattr(solara.state, "get_backend", lambda: None)
    data = _call_resourcez()
    assert data["state"]["status"] == "off"


def test_resourcez_state_block_degraded(backend):
    breaker = solara.state.get_breaker()
    for _ in range(solara.server.settings.state.breaker_failures):
        breaker.record_failure()
    assert breaker.state == "open"
    data = _call_resourcez()
    assert data["state"]["status"] == "degraded"
    assert data["state"]["circuit_breaker"] == "open"


# --- /resourcez key-label redaction (persist keys may embed PII) ---------------------------


def test_resourcez_redacts_key_labels_in_production(backend, monkeypatch):
    # a persist key can embed an identifier (recommended pattern: key="user:<id>:...")
    solara.state.stats().record_sync("kern-x", {"user:42:matches": 128})
    monkeypatch.setattr(solara.server.settings.main, "mode", "production")
    monkeypatch.setattr(solara.server.settings.main, "resourcez_token", "")
    data = _call_resourcez()
    keys = [row["key"] for row in data["state"]["sync_by_key"]]
    # label hashed, identifier gone, but the numbers (and aggregates) survive
    assert keys and all(k.startswith("sha256:") for k in keys)
    assert all("user:42" not in k for k in keys)
    assert data["state"]["sync_by_key"][0]["bytes"] == 128
    assert data["state"]["sync_count"] >= 1


def test_resourcez_full_detail_with_bearer_token(backend, monkeypatch):
    solara.state.stats().record_sync("kern-x", {"user:42:matches": 128})
    monkeypatch.setattr(solara.server.settings.main, "mode", "production")
    monkeypatch.setattr(solara.server.settings.main, "resourcez_token", "s3cr3t")
    keys = [row["key"] for row in _call_resourcez(auth="Bearer s3cr3t")["state"]["sync_by_key"]]
    assert "user:42:matches" in keys
    # a wrong / missing token degrades to the redacted view, never an error
    wrong = [row["key"] for row in _call_resourcez(auth="Bearer nope")["state"]["sync_by_key"]]
    assert all(k.startswith("sha256:") for k in wrong)
    missing = [row["key"] for row in _call_resourcez()["state"]["sync_by_key"]]
    assert all(k.startswith("sha256:") for k in missing)


def test_resourcez_full_detail_in_development(backend, monkeypatch):
    solara.state.stats().record_sync("kern-x", {"user:42:matches": 128})
    monkeypatch.setattr(solara.server.settings.main, "mode", "development")
    keys = [row["key"] for row in _call_resourcez()["state"]["sync_by_key"]]
    assert "user:42:matches" in keys  # localhost dev: no redaction, no token needed


# --- fail-closed eviction route (§6.4) ----------------------------------------------------


def _call_evict(kernel_id, cookie_session_id):
    from solara.server.starlette import evict

    request = Mock()
    request.path_params = {"kernel_id": kernel_id}
    request.cookies = {"solara-session-id": cookie_session_id} if cookie_session_id is not None else {}
    return asyncio.run(evict(request))


def test_evict_route_gating(backend, monkeypatch):
    session_id, kernel_id = "sess-evict", "kern-evict"
    context = kc.initialize_virtual_kernel(session_id, kernel_id, Mock())

    # production mode -> route disabled (fail-closed), even with test_eviction on
    monkeypatch.setattr(solara.server.settings.state, "test_eviction", True)
    monkeypatch.setattr(solara.server.settings.main, "mode", "production")
    assert _call_evict(kernel_id, session_id).status_code == 404
    assert not context.closed_event.is_set()

    # enabled (non-production) but wrong session cookie -> 403
    monkeypatch.setattr(solara.server.settings.main, "mode", "development")
    assert _call_evict(kernel_id, "wrong-session").status_code == 403
    assert not context.closed_event.is_set()

    # unknown kernel -> 404
    assert _call_evict("does-not-exist", session_id).status_code == 404

    # correct session -> 200 and the context is closed with reason "evicted"
    assert _call_evict(kernel_id, session_id).status_code == 200
    assert context.closed_event.is_set()
    assert context.close_reason == "evicted"
    assert kernel_id not in kc.contexts


def test_evict_route_disabled_by_default(backend):
    # without SOLARA_STATE_TEST_EVICTION the route is off even outside production
    import solara.server.settings as server_settings

    kernel_id = "kern-evict-default"
    kc.initialize_virtual_kernel("sess", kernel_id, Mock())
    assert server_settings.main.mode != "production" or True  # mode is whatever the env is
    assert _call_evict(kernel_id, "sess").status_code == 404


# --- ws (solara.control comm) eviction, the path simulateFailover uses (§6.4) --------------


class _FakeComm:
    """The comm interface solara_comm_target needs: on_msg registration + send capture."""

    def __init__(self):
        self.sent: list = []
        self._handler = None

    def on_msg(self, handler):
        self._handler = handler

    def send(self, data):
        self.sent.append(data)

    def dispatch(self, data):
        assert self._handler is not None
        self._handler({"content": {"data": data}})


def _comm_evict(context):
    """Register the control comm target inside ``context`` and dispatch an evict message."""
    from solara.server.app import solara_comm_target

    fake = _FakeComm()
    with context:
        solara_comm_target(fake, None)
        fake.dispatch({"method": "evict"})
    return fake.sent


def test_evict_comm_refused_when_gated(backend, monkeypatch):
    # gate off (default test_eviction=False): refused reply, context untouched. The ws evict
    # needs NO session check - the comm only exists on the kernel's own authenticated socket.
    context = kc.initialize_virtual_kernel("sess-ws-evict", "kern-ws-evict", Mock())
    assert _comm_evict(context) == [{"method": "evict", "status": "refused"}]
    assert not context.closed_event.is_set()

    # production mode refuses even with the test flag on (fail-closed)
    monkeypatch.setattr(solara.server.settings.state, "test_eviction", True)
    monkeypatch.setattr(solara.server.settings.main, "mode", "production")
    assert _comm_evict(context) == [{"method": "evict", "status": "refused"}]
    assert not context.closed_event.is_set()


def test_evict_comm_closes_context(backend, monkeypatch):
    monkeypatch.setattr(solara.server.settings.state, "test_eviction", True)
    monkeypatch.setattr(solara.server.settings.main, "mode", "development")
    kernel_id = "kern-ws-evict-ok"
    context = kc.initialize_virtual_kernel("sess-ws-evict-ok", kernel_id, Mock())

    sent = _comm_evict(context)
    # the reply is sent BEFORE the close starts (close tears down the websocket)
    assert sent == [{"method": "evict", "status": "evicted"}]
    # the close runs on a separate thread (never re-entrantly on the kernel's message thread)
    assert context.closed_event.wait(timeout=5)
    assert context.close_reason == "evicted"
    assert kernel_id not in kc.contexts


# --- bail-out storm valve (§4.3) ----------------------------------------------------------


def _can_recover_of(recovery_failed: bool):
    from solara.server.app import _can_recover

    ctx = Mock()
    ctx.id = "kern-valve"
    ctx.state_persistence = Mock(recovery_failed=recovery_failed)
    return _can_recover(ctx)


def test_bailout_storm_valve_flips_recovery_failed_to_soft_remount(backend, monkeypatch):
    monkeypatch.setattr(solara.server.settings.state, "auto_remount", None)
    monkeypatch.setattr(solara.server.settings.state, "bailout_storm_threshold", 0.5)
    # a single (non-storm) bail-out: recovery-failed context must hard-refresh
    solara.state.stats().record_restore_attempt(bailed_out=True)
    assert _can_recover_of(recovery_failed=True) is False
    # a storm: >= threshold bail-outs over the min sample -> valve trips, soft-remount instead
    for i in range(12):
        solara.state.stats().record_restore_attempt(bailed_out=(i < 9))  # 9/12 well past 0.5
    assert _can_recover_of(recovery_failed=True) is True
    # a healthy context is never affected by the valve
    assert _can_recover_of(recovery_failed=False) is True


# --- public API (§5.5b) -------------------------------------------------------------------


def test_kernel_closed_event_requires_context(no_kernel_context):
    # no_kernel_context removes conftest's ambient context for this test
    with pytest.raises(RuntimeError):
        solara.kernel_closed_event()


def test_kernel_closed_event_and_state_generation(backend, no_kernel_context):
    solara.reactive(0, persist=True, key="test.server.api")
    context = kc.initialize_virtual_kernel("sess-api", "kern-api", Mock())
    assert context.state_persistence is not None
    with context:
        assert solara.kernel_closed_event() is context.closed_event
        assert solara.state_generation() == context.state_persistence.generation
    # outside the context again -> raises
    with pytest.raises(RuntimeError):
        solara.kernel_closed_event()
