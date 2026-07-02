import os
import threading

import pytest

import solara.settings
import solara.state as state
from solara.state import MemoryStateBackend

# session-HMACs and envelope contents are opaque bytes to the backend, so these tests use
# plain byte literals rather than real signed envelopes.
SESSION_A = b"session-hmac-a"
SESSION_B = b"session-hmac-b"
TTL = 60.0


@pytest.fixture(params=["memory", "fakeredis", "redis"])
def backend(request):
    """The shared four-verb contract, parametrized across every backend.

    - ``memory``: the in-process reference backend.
    - ``fakeredis``: the real RedisStateBackend (Lua scripts and all) driven by an in-process
      fakeredis[lua] server, so the fenced Lua is exercised on every contract assertion.
    - ``redis``: the same against a real server; opt-in via ``SOLARA_TEST_REDIS_URL`` (a throwaway
      db - the fixture ``flushdb()``s around each test), skipped otherwise so CI can enable it later.
    """
    if request.param == "memory":
        yield MemoryStateBackend()
        return
    if request.param == "fakeredis":
        fakeredis = pytest.importorskip("fakeredis")
        from solara.state.redis import RedisStateBackend

        server = fakeredis.FakeServer()
        yield RedisStateBackend(client=fakeredis.FakeRedis(server=server))
        return
    # real redis (opt-in): the same contract against a live server
    url = os.environ.get("SOLARA_TEST_REDIS_URL")
    if not url:
        pytest.skip("set SOLARA_TEST_REDIS_URL to run the contract against a real redis server")
    redis = pytest.importorskip("redis")
    from solara.state.redis import RedisStateBackend

    client = redis.Redis.from_url(url, decode_responses=False)
    client.flushdb()
    try:
        yield RedisStateBackend(client=client)
    finally:
        client.flushdb()


def test_miss_writes_nothing(backend):
    result = backend.takeover("k", SESSION_A, "v1")
    assert result.reason == "miss"
    assert result.generation == 1
    assert result.fields == {}
    # a miss must not have created anything: a second takeover is still a miss
    assert backend.peek_generation("k") is None
    assert backend.takeover("k", SESSION_A, "v1").reason == "miss"


def test_flush_creates_with_identity_on_absent_key(backend):
    assert backend.flush("k", 1, {"reactive:x": b"e1"}, TTL, SESSION_A, "v1") is True
    # identity was written by the flush, so a matching takeover restores
    result = backend.takeover("k", SESSION_A, "v1")
    assert result.reason == "restored"
    assert result.fields == {"reactive:x": b"e1"}


def test_restored_bumps_generation_and_returns_fields(backend):
    backend.flush("k", 1, {"reactive:x": b"e1", "reactive:y": b"e2"}, TTL, SESSION_A, "v1")
    first = backend.takeover("k", SESSION_A, "v1")
    assert first.reason == "restored"
    assert first.generation == 2
    assert first.fields == {"reactive:x": b"e1", "reactive:y": b"e2"}
    # each takeover bumps again (fencing)
    assert backend.takeover("k", SESSION_A, "v1").generation == 3


def test_identity_mismatch_grants_no_write_rights_and_leaves_data(backend):
    backend.flush("k", 1, {"reactive:x": b"e1"}, TTL, SESSION_A, "v1")
    result = backend.takeover("k", SESSION_B, "v1")
    assert result.reason == "identity-mismatch"
    assert result.generation == 0
    assert result.fields == {}
    # a generation-0 flush must be refused, so an impostor cannot write
    assert backend.flush("k", 0, {"reactive:x": b"evil"}, TTL, SESSION_B, "v1") is False
    # the original owner's data is intact
    restored = backend.takeover("k", SESSION_A, "v1")
    assert restored.reason == "restored"
    assert restored.fields == {"reactive:x": b"e1"}


def test_schema_reset_deletes(backend):
    backend.flush("k", 1, {"reactive:x": b"e1"}, TTL, SESSION_A, "v1")
    result = backend.takeover("k", SESSION_A, "v2")
    assert result.reason == "schema-reset"
    assert result.generation == 1
    assert result.fields == {}
    # the hash was deleted, so it is gone entirely
    assert backend.peek_generation("k") is None
    assert backend.takeover("k", SESSION_A, "v1").reason == "miss"


def test_fenced_flush_rejects_stale_generation(backend):
    backend.flush("k", 1, {"reactive:x": b"e1"}, TTL, SESSION_A, "v1")
    # a takeover moves ownership to generation 2
    assert backend.takeover("k", SESSION_A, "v1").generation == 2
    assert backend.peek_generation("k") == 2
    # a flush still claiming generation 1 is stale and must write nothing
    assert backend.flush("k", 1, {"reactive:x": b"stale"}, TTL, SESSION_A, "v1") is False
    # a flush from the future (generation not yet reached) is equally rejected
    assert backend.flush("k", 3, {"reactive:x": b"future"}, TTL, SESSION_A, "v1") is False
    # only the current owner (generation 2) may write
    assert backend.flush("k", 2, {"reactive:x": b"fresh"}, TTL, SESSION_A, "v1") is True
    # neither the stale nor the future write landed
    assert backend.takeover("k", SESSION_A, "v1").fields == {"reactive:x": b"fresh"}


def test_flush_generation_zero_always_rejected(backend):
    assert backend.flush("k", 0, {"reactive:x": b"e1"}, TTL, SESSION_A, "v1") is False
    assert backend.peek_generation("k") is None


def test_fenced_delete(backend):
    backend.flush("k", 1, {"reactive:x": b"e1"}, TTL, SESSION_A, "v1")
    assert backend.delete("k", 2) is False  # wrong generation
    assert backend.peek_generation("k") == 1
    assert backend.delete("k", 1) is True
    assert backend.peek_generation("k") is None
    assert backend.delete("k") is False  # nothing to delete


def test_unfenced_delete(backend):
    backend.flush("k", 5, {"reactive:x": b"e1"}, TTL, SESSION_A, "v1")
    assert backend.delete("k") is True
    assert backend.peek_generation("k") is None


def test_ttl_expiry_via_monkeypatched_clock(backend):
    if not isinstance(backend, MemoryStateBackend):
        # redis has its own clock; clock injection is memory-only. Redis TTL (EXPIRE set on
        # create, refreshed on flush and takeover) is covered in state_redis_test.py.
        pytest.skip("clock injection is memory-only; redis TTL is covered in state_redis_test.py")
    now = [0.0]
    backend._clock = lambda: now[0]
    backend.flush("k", 1, {"reactive:x": b"e1"}, 10.0, SESSION_A, "v1")
    assert backend.peek_generation("k") == 1
    now[0] = 9.9
    assert backend.peek_generation("k") == 1
    now[0] = 10.0  # deadline reached (>=)
    assert backend.peek_generation("k") is None
    # an expired key behaves as absent for takeover too
    assert backend.takeover("k", SESSION_A, "v1").reason == "miss"


def test_concurrent_flushes_never_interleave_partially(backend):
    backend.flush("k", 1, {}, TTL, SESSION_A, "v1")

    barrier = threading.Barrier(2)
    errors = []

    def writer(prefix):
        try:
            barrier.wait()
            for i in range(200):
                ok = backend.flush("k", 1, {f"{prefix}:{i}": b"x"}, TTL, SESSION_A, "v1")
                assert ok
        except Exception as exc:  # pragma: no cover
            errors.append(exc)

    threads = [threading.Thread(target=writer, args=(p,)) for p in ("a", "b")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert not errors
    result = backend.takeover("k", SESSION_A, "v1")
    # both writers' fields are all present, none lost or corrupted by interleaving
    assert len(result.fields) == 400
    assert all(v == b"x" for v in result.fields.values())


# --- registry / settings validation ---------------------------------------


def test_get_backend_disabled_by_default(monkeypatch):
    monkeypatch.setattr(solara.settings.state, "backend", "")
    state.reset_backend()
    try:
        assert state.get_backend() is None
    finally:
        state.reset_backend()


def test_get_backend_memory_singleton(monkeypatch):
    monkeypatch.setattr(solara.settings.state, "backend", "memory")
    state.reset_backend()
    try:
        one = state.get_backend()
        assert isinstance(one, MemoryStateBackend)
        assert state.get_backend() is one  # process-wide singleton
    finally:
        state.reset_backend()


def test_get_backend_unknown_raises(monkeypatch):
    monkeypatch.setattr(solara.settings.state, "backend", "does-not-exist")
    state.reset_backend()
    try:
        with pytest.raises(ValueError):
            state.get_backend()
    finally:
        state.reset_backend()


def test_validate_state_settings_ok_when_disabled(monkeypatch):
    monkeypatch.setattr(solara.settings.state, "backend", "")
    monkeypatch.setattr(solara.settings.state, "secret_keys", "")
    monkeypatch.setattr(solara.settings.state, "allow_pickle", False)
    state.validate_state_settings()  # no error


def test_validate_state_settings_requires_secrets_when_enabled(monkeypatch):
    monkeypatch.setattr(solara.settings.state, "backend", "memory")
    monkeypatch.setattr(solara.settings.state, "secret_keys", "")
    with pytest.raises(ValueError):
        state.validate_state_settings()


def test_validate_state_settings_rejects_placeholder_secret(monkeypatch):
    monkeypatch.setattr(solara.settings.state, "backend", "memory")
    monkeypatch.setattr(solara.settings.state, "secret_keys", "change me")
    with pytest.raises(ValueError):
        state.validate_state_settings()


def test_validate_state_settings_ok_with_real_secret(monkeypatch):
    monkeypatch.setattr(solara.settings.state, "backend", "memory")
    monkeypatch.setattr(solara.settings.state, "secret_keys", "a-real-secret")
    monkeypatch.setattr(solara.settings.state, "allow_pickle", False)
    state.validate_state_settings()  # no error


def test_validate_state_settings_pickle_gate_needs_real_secret(monkeypatch):
    monkeypatch.setattr(solara.settings.state, "backend", "")
    monkeypatch.setattr(solara.settings.state, "secret_keys", "")
    monkeypatch.setattr(solara.settings.state, "allow_pickle", True)
    with pytest.raises(ValueError):
        state.validate_state_settings()
