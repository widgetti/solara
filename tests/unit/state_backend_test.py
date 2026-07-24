import os
import threading

# fakeredis[lua] is a hard test dependency (solara-meta dev extra): the fenced-Lua contract
# tests must always run, never silently skip. A missing install fails loudly here.
import fakeredis
import pytest
import redis

import solara.server.settings
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
        from solara.state.redis import RedisStateBackend

        server = fakeredis.FakeServer()
        yield RedisStateBackend(client=fakeredis.FakeRedis(server=server))
        return
    # real redis (opt-in): the same contract against a live server
    url = os.environ.get("SOLARA_TEST_REDIS_URL")
    if not url:
        pytest.skip("set SOLARA_TEST_REDIS_URL to run the contract against a real redis server")
        return  # mypy does not narrow Optional through pytest.skip here
    from solara.state.redis import RedisStateBackend

    client = redis.Redis.from_url(url, decode_responses=False)
    client.flushdb()
    try:
        yield RedisStateBackend(client=client)
    finally:
        client.flushdb()


def test_miss_claims_the_key(backend):
    result = backend.takeover("k", SESSION_A, "v1")
    assert result.reason == "miss"
    assert result.generation == 1
    assert result.fields == {}
    # claim-on-miss: the fresh-start generation is immediately visible to peek_generation, so a
    # kernel that never flushes anything (e.g. a login form pre-login) is still FENCEABLE - its
    # node can detect a later takeover elsewhere and supersede the zombie context. (Before the
    # claim, peek stayed None until the first flush and such kernels were unfenceable.)
    assert backend.peek_generation("k") == 1
    # a repeat takeover by the same session is now a restore of the claimed (empty) key
    again = backend.takeover("k", SESSION_A, "v1")
    assert again.reason == "restored"
    assert again.generation == 2
    assert again.fields == {}


def test_claimed_key_supersedes_never_flushed_owner(backend):
    # node A claims on miss and never flushes (nothing persisted yet)
    a = backend.takeover("k", SESSION_A, "v1")
    assert (a.reason, a.generation) == ("miss", 1)
    # node B (same browser session) takes over the same kernel id
    b = backend.takeover("k", SESSION_A, "v1")
    assert b.generation == 2
    # A can now SEE it is behind - exactly the _reuse_context_is_stale comparison
    stored = backend.peek_generation("k")
    assert stored == 2
    assert stored != a.generation
    # and A's late first-flush is fenced out
    assert backend.flush("k", a.generation, {"reactive:x": b"stale"}, TTL, SESSION_A, "v1") is False


def test_claimed_key_refuses_foreign_session(backend):
    # the claimed-but-never-flushed key follows the same identity rule as a flushed one
    backend.takeover("k", SESSION_A, "v1")
    result = backend.takeover("k", SESSION_B, "v1")
    assert result.reason == "identity-mismatch"
    assert result.generation == 0
    assert result.fields == {}
    # the foreign session gained no write rights
    assert backend.flush("k", 2, {"reactive:x": b"evil"}, TTL, SESSION_B, "v1") is False


def test_claim_expires_with_ttl(backend):
    if isinstance(backend, MemoryStateBackend):
        now = [0.0]
        backend._clock = lambda: now[0]
        backend.takeover("k", SESSION_A, "v1")
        assert backend.peek_generation("k") == 1
        # the claim carries the default ttl (hours in practice); jump far past any sane value
        now[0] = 10 * 24 * 3600.0
        assert backend.peek_generation("k") is None
        # an expired claim behaves as absent: the next takeover is a fresh miss+claim
        assert backend.takeover("k", SESSION_A, "v1").reason == "miss"
    else:
        # redis: the claim must have set an EXPIRE (abandoned claims may not live forever)
        backend.takeover("k", SESSION_A, "v1")
        ttl = backend.client.ttl(backend._key("k"))
        assert ttl > 0


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


def test_takeover_verify_any_survives_key_rotation(backend, monkeypatch):
    # State written under an OLD primary key must still authenticate after a NEW primary is
    # promoted - otherwise a routine key rotation orphans every in-flight persisted kernel.
    monkeypatch.setattr(solara.server.settings.state, "secret_keys", "KEY-OLD")
    old_primary = state.session_hmac("sid-rot")
    assert backend.flush("kr", 1, {"reactive:x": b"e1"}, TTL, old_primary, "v1") is True

    # rotate: new primary first, old still configured for verification (two-phase rotation)
    monkeypatch.setattr(solara.server.settings.state, "secret_keys", "KEY-NEW,KEY-OLD")
    result = backend.takeover("kr", state.session_hmacs("sid-rot"), "v1")
    assert result.reason == "restored"
    assert result.fields == {"reactive:x": b"e1"}

    # the reconnect that drove that takeover flushes with the NEW primary, migrating identity forward
    assert backend.flush("kr", result.generation, {"reactive:x": b"e2"}, TTL, state.session_hmac("sid-rot"), "v1") is True

    # once the old key is dropped entirely, the migrated identity still authenticates
    monkeypatch.setattr(solara.server.settings.state, "secret_keys", "KEY-NEW")
    assert backend.takeover("kr", state.session_hmacs("sid-rot"), "v1").reason == "restored"
    # a different session is still rejected - verify-any did not weaken identity
    assert backend.takeover("kr", state.session_hmacs("other-sid"), "v1").reason == "identity-mismatch"


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
    # the old-tag data was deleted, and (same unfenceable-zombie hole as a miss) the key was
    # re-CLAIMED for the caller under the new tag: generation 1, no data fields
    assert backend.peek_generation("k") == 1
    assert backend.takeover("k", SESSION_A, "v2").fields == {}
    # a takeover with the old tag hits the claimed key and resets again (schema flapping is
    # always a reset, never a silent restore across tags)
    assert backend.takeover("k", SESSION_A, "v1").reason == "schema-reset"


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


def test_flush_refuses_to_resurrect_missing_key_at_stale_generation(backend):
    # an older instance still holding a high generation whose key was deleted/evicted must NOT be
    # able to recreate it at that stale generation (which would revive stale data and fence out the
    # legitimate new owner). Only a fresh-start (generation 1) create is allowed on a missing key.
    assert backend.flush("k", 4, {"reactive:x": b"stale"}, TTL, SESSION_A, "v1") is False
    assert backend.peek_generation("k") is None  # nothing was resurrected
    # the fresh-start create still works, and a new owner establishes cleanly
    assert backend.flush("k", 1, {"reactive:x": b"fresh"}, TTL, SESSION_A, "v1") is True
    assert backend.takeover("k", SESSION_A, "v1").fields == {"reactive:x": b"fresh"}


def test_fenced_delete(backend):
    backend.flush("k", 1, {"reactive:x": b"e1"}, TTL, SESSION_A, "v1")
    assert backend.delete("k", 2) is False  # wrong generation
    assert backend.peek_generation("k") == 1
    assert backend.delete("k", 1) is True
    assert backend.peek_generation("k") is None
    assert backend.delete("k") is False  # nothing to delete


def test_unfenced_delete(backend):
    # reach a non-1 generation the legitimate way (create at 1, then takeover bumps), so the
    # unfenced delete is shown to ignore a *stored* generation > 1
    backend.flush("k", 1, {"reactive:x": b"e1"}, TTL, SESSION_A, "v1")
    backend.takeover("k", SESSION_A, "v1")  # -> gen 2
    backend.takeover("k", SESSION_A, "v1")  # -> gen 3
    assert backend.peek_generation("k") == 3
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
    monkeypatch.setattr(solara.server.settings.state, "backend", "")
    state.reset_backend()
    try:
        assert state.get_backend() is None
    finally:
        state.reset_backend()


def test_get_backend_memory_singleton(monkeypatch):
    monkeypatch.setattr(solara.server.settings.state, "backend", "memory")
    state.reset_backend()
    try:
        one = state.get_backend()
        assert isinstance(one, MemoryStateBackend)
        assert state.get_backend() is one  # process-wide singleton
    finally:
        state.reset_backend()


def test_get_backend_unknown_raises(monkeypatch):
    monkeypatch.setattr(solara.server.settings.state, "backend", "does-not-exist")
    state.reset_backend()
    try:
        with pytest.raises(ValueError):
            state.get_backend()
    finally:
        state.reset_backend()


def test_validate_state_settings_ok_when_disabled(monkeypatch):
    monkeypatch.setattr(solara.server.settings.state, "backend", "")
    monkeypatch.setattr(solara.server.settings.state, "secret_keys", "")
    monkeypatch.setattr(solara.server.settings.state, "allow_pickle", False)
    state.validate_state_settings()  # no error


def test_validate_state_settings_requires_secrets_when_enabled(monkeypatch):
    monkeypatch.setattr(solara.server.settings.state, "backend", "memory")
    monkeypatch.setattr(solara.server.settings.state, "secret_keys", "")
    with pytest.raises(ValueError):
        state.validate_state_settings()


def test_validate_state_settings_rejects_placeholder_secret(monkeypatch):
    monkeypatch.setattr(solara.server.settings.state, "backend", "memory")
    monkeypatch.setattr(solara.server.settings.state, "secret_keys", "change me")
    with pytest.raises(ValueError):
        state.validate_state_settings()


def test_validate_state_settings_ok_with_real_secret(monkeypatch):
    monkeypatch.setattr(solara.server.settings.state, "backend", "memory")
    monkeypatch.setattr(solara.server.settings.state, "secret_keys", "a-real-secret")
    monkeypatch.setattr(solara.server.settings.state, "allow_pickle", False)
    state.validate_state_settings()  # no error


def test_validate_state_settings_pickle_gate_needs_real_secret(monkeypatch):
    monkeypatch.setattr(solara.server.settings.state, "backend", "")
    monkeypatch.setattr(solara.server.settings.state, "secret_keys", "")
    monkeypatch.setattr(solara.server.settings.state, "allow_pickle", True)
    with pytest.raises(ValueError):
        state.validate_state_settings()
