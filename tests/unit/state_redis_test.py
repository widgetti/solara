"""Redis-backend-specific tests (commit 3 of state persistence).

The shared four-verb contract is exercised against RedisStateBackend (via fakeredis[lua]) in
state_backend_test.py's parametrized suite. This file adds the tests that only make sense for the
real Lua/hash backend - atomicity/no-partial-write proofs by dumping the raw hash, TTL behaviour,
byte fidelity, prefixing, the corrupted-hash hard-reject, and the lazy import error - plus two
end-to-end failover tests that drive the commit-2 server lifecycle over a real RedisStateBackend
backed by an in-process fakeredis server (single-process failover, and A->B->A across two backend
instances sharing ONE FakeServer, i.e. the two-instances-one-redis topology in-process).
"""

import sys
import time
from typing import Callable
from unittest.mock import Mock

# hard test dependency (solara-meta dev extra): these tests must run, never silently skip
import fakeredis
import pytest

import solara
import solara.server.settings
import solara.state
import solara.server.kernel_context as kc
from solara.server import kernel
from solara.state import FlushOutcome, session_hmac

from solara.state.redis import RedisStateBackend

SESSION_A = b"session-hmac-a"
SESSION_B = b"session-hmac-b"
TTL = 60.0
SCHEMA_TAG = "redis-e2e-schema-1"


def _new_backend(server=None):
    server = server or fakeredis.FakeServer()
    return RedisStateBackend(client=fakeredis.FakeRedis(server=server))


@pytest.fixture
def rb():
    return _new_backend()


# --- atomicity / no-partial-write proofs (raw hash dump) ----------------------------------


def test_identity_mismatch_leaves_hash_byte_for_byte(rb):
    rb.flush("k", 1, {"reactive:x": b"\x00\x01\xfe\xff"}, TTL, SESSION_A, "v1")
    key = rb._key("k")
    before = rb.client.hgetall(key)
    result = rb.takeover("k", SESSION_B, "v1")
    assert result.reason == "identity-mismatch"
    assert result.generation == 0
    # an atomic takeover on a foreign session writes NOTHING: the hash is byte-for-byte unchanged
    # (in particular the generation was not bumped)
    assert rb.client.hgetall(key) == before
    assert rb.peek_generation("k") == 1


def test_flush_rejection_writes_nothing(rb):
    rb.flush("k", 1, {"reactive:x": b"e1"}, TTL, SESSION_A, "v1")
    assert rb.takeover("k", SESSION_A, "v1").generation == 2  # ownership moved to gen 2
    key = rb._key("k")
    before = rb.client.hgetall(key)
    # a stale-generation flush that also tries to add a new field must land NONE of it
    assert rb.flush("k", 1, {"reactive:x": b"stale", "reactive:new": b"n"}, TTL, SESSION_A, "v1") is False
    assert rb.client.hgetall(key) == before


def test_ttl_present_and_refreshed(rb, monkeypatch):
    # takeover has no ttl arg; it refreshes using the settings TTL, so make that deterministic
    monkeypatch.setattr(solara.server.settings.state, "ttl", "100s")
    key = rb._key("k")
    rb.flush("k", 1, {"reactive:x": b"e1"}, TTL, SESSION_A, "v1")
    assert 0 < rb.client.ttl(key) <= 60  # EXPIRE set on first flush, from the passed ttl

    rb.client.expire(key, 5)
    rb.flush("k", 1, {"reactive:y": b"e2"}, TTL, SESSION_A, "v1")
    assert rb.client.ttl(key) > 5  # a subsequent flush refreshed the TTL

    rb.client.expire(key, 5)
    rb.takeover("k", SESSION_A, "v1")
    assert rb.client.ttl(key) > 60  # takeover refreshed it, using the longer (100s) settings TTL


def test_generation_survives_as_int_across_hincrby(rb):
    rb.flush("k", 1, {}, TTL, SESSION_A, "v1")
    for expected in (2, 3, 4):
        result = rb.takeover("k", SESSION_A, "v1")
        assert result.generation == expected
        assert isinstance(result.generation, int)
    peeked = rb.peek_generation("k")
    assert peeked == 4
    assert isinstance(peeked, int)


def test_envelope_bytes_round_trip_exactly(rb):
    # every byte value, plus explicit NUL/0xFF, must survive the Lua/hash round trip untouched
    blob = bytes(range(256)) + b"\x00\xff\x00\xff"
    rb.flush("k", 1, {"reactive:b": blob}, TTL, SESSION_A, "v1")
    result = rb.takeover("k", SESSION_A, "v1")
    assert result.fields["reactive:b"] == blob


def test_prefix_respected(monkeypatch):
    monkeypatch.setattr(solara.server.settings.state, "prefix", "custom:pfx:")
    be = _new_backend()  # constructed AFTER the prefix change, so it reads the new prefix
    be.flush("kk", 1, {"reactive:x": b"e"}, TTL, SESSION_A, "v1")
    assert be.client.exists("custom:pfx:kk")
    assert not be.client.exists("solara:state:kk")


def test_missing_session_id_hard_rejects(rb):
    # a hash created by something else / corrupted: data + version + generation but NO __session_id__
    key = rb._key("k")
    rb.client.hset(key, mapping={"__generation__": "1", "__version__": "v1", "reactive:x": b"e1"})
    result = rb.takeover("k", SESSION_A, "v1")
    assert result.reason == "identity-mismatch"  # missing identity is a hard reject (§5.1)
    assert result.generation == 0
    assert rb.peek_generation("k") == 1  # nothing bumped or written


def test_lazy_import_error_message(monkeypatch):
    # make `import redis` fail even though the package is installed, to prove the message
    monkeypatch.setitem(sys.modules, "redis", None)
    monkeypatch.setattr(solara.server.settings.state, "url", "redis://localhost:6379/0")
    with pytest.raises(ImportError) as excinfo:
        RedisStateBackend()  # no injected client -> _make_client -> import redis
    message = str(excinfo.value)
    assert "solara[redis]" in message
    assert "redis" in message


def test_make_client_requires_url(monkeypatch):
    monkeypatch.setattr(solara.server.settings.state, "url", "")
    with pytest.raises(ValueError):
        RedisStateBackend()  # no url and no injected client


# --- end-to-end failover over fakeredis (server lifecycle from commit 2) -------------------


def wait_until(pred: Callable[[], bool], timeout: float = 2.0, interval: float = 0.005) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if pred():
            return True
        time.sleep(interval)
    return pred()


@pytest.fixture(autouse=True)
def state_env(monkeypatch):
    from solara.state import derive, persist, stats

    monkeypatch.setattr(solara.server.settings.state, "secret_keys", "unit-test-secret-key")
    monkeypatch.setattr(solara.server.settings.state, "schema_tag", SCHEMA_TAG)
    monkeypatch.setattr(solara.server.settings.state, "flush_debounce", "10ms")
    derive._reset_registry()
    persist._reset_registry()
    persist._attached_managers.clear()
    stats()._reset()
    solara.state.reset_breaker()
    yield
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


def test_e2e_single_process_failover_over_fakeredis(monkeypatch):
    be = _new_backend()
    monkeypatch.setattr(solara.state, "get_backend", lambda: be)

    r = solara.reactive("start", persist=True, key="test.redis.failover")
    session_id, kernel_id = "sess-r-failover", "kern-r-failover"

    context = kc.initialize_virtual_kernel(session_id, kernel_id, Mock())
    context.page_connect("page-1")
    assert context.state_persistence is not None
    with context:
        r.value = "restored-value"
    # wait on the backend observable, not the dirty set (drained before the write lands)
    assert wait_until(lambda: be.peek_generation(kernel_id) == 1)

    # evict (the server half of simulateFailover): flush-and-leave + drop the in-memory context
    context.close(reason="evicted")
    assert kernel_id not in kc.contexts
    assert be.peek_generation(kernel_id) == 1  # the redis hash survived (no delete on evict)

    # reconnect lands on a fresh context; restore runs for real via the Lua takeover
    context2 = kc.initialize_virtual_kernel(session_id, kernel_id, Mock())
    assert context2 is not context
    assert context2.state_persistence is not None
    with context2:
        assert r.value == "restored-value"


def test_e2e_double_reconnect_two_backends_one_server(monkeypatch):
    # the two-instances-one-redis topology, in-process: two RedisStateBackend instances sharing
    # ONE FakeServer (as two solara-server processes would share one real Redis)
    server = fakeredis.FakeServer()
    backend_a = _new_backend(server)
    backend_b = _new_backend(server)
    monkeypatch.setattr(solara.state, "get_backend", lambda: backend_a)

    r = solara.reactive("v0", persist=True, key="test.redis.abab")
    session_id, kernel_id = "sess-r-abab", "kern-r-abab"
    shmac = session_hmac(session_id)

    # instance A flushes "from-A" at generation 1. Flush synchronously: since takeover claims
    # the key on a miss, peek==1 no longer means "A's flush landed" — a debounced flush still
    # in flight here would race B's takeover below and get fenced, flipping this into the
    # (designed, §5.5) reclaim-once fight instead of the zombie scenario this test pins.
    context_a = kc.initialize_virtual_kernel(session_id, kernel_id, Mock())
    context_a.page_connect("pageA")
    with context_a:
        r.value = "from-A"
    manager_a = context_a.state_persistence
    assert manager_a is not None
    assert manager_a.flush_now() == FlushOutcome.OK
    assert backend_a.peek_generation(kernel_id) == 1
    # the page's websocket drops BEFORE the reconnect lands on B (what a real failover does).
    # Also required for determinism in-process: toestand scopes listeners by kernel *id* (see
    # watch()'s docstring), so B's r.value below re-marks A dirty; A's debounced flush then gets
    # fenced, and a fenced kernel WITH a connected page would take the (designed, §5.5)
    # reclaim-once path — gen 3, defeating the zombie scenario this test pins. Disconnected,
    # a fenced A is an orphan: it concedes and closes as superseded — the same outcome the
    # reconnect's staleness check produces, whichever fires first.
    context_a.page_disconnect("pageA")

    # instance B (the second backend on the same server) takes over -> gen 2, then flushes "from-B"
    result_b = backend_b.takeover(kernel_id, shmac, SCHEMA_TAG)
    assert result_b.generation == 2
    context_b = kc.VirtualKernelContext(id=kernel_id, kernel=kernel.Kernel(), session_id=session_id)
    manager_b = solara.state.attach(context_b, backend_b, session_hmac=shmac, schema_tag=SCHEMA_TAG, generation=result_b.generation, envelopes=result_b.fields)
    with context_b:
        r.value = "from-B"
    assert manager_b.flush_now() == FlushOutcome.OK
    assert backend_b.peek_generation(kernel_id) == 2

    # reconnect on instance A: the reuse branch peeks gen 2 != its remembered gen 1, closes A as
    # superseded, creates a fresh context, and restores B's latest value through the Lua takeover
    context_new = kc.initialize_virtual_kernel(session_id, kernel_id, Mock())
    assert context_new is not context_a
    assert context_a.closed_event.is_set()
    assert context_a.close_reason == "superseded"
    assert context_new.state_persistence is not None
    with context_new:
        assert r.value == "from-B"
