"""Tests for opt-in reactive state persistence (commit 1: API, registry, manager).

Covers the design doc's commit-1 matrix: key resolution (derived / explicit / class
attribute / factory refusal), the restore seam in both mutation-detection modes,
all-or-nothing bail-out, per-context dirty-tracking, fenced flush + keys-stay-dirty-
until-ACK, serialize-failure disable, and the zero-overhead guarantee for
non-persisted reactives. Uses MemoryStateBackend (same envelope-byte fidelity as
Redis) and real VirtualKernelContexts to simulate two kernels/instances.
"""

import dataclasses
import importlib
import itertools
import sys
import textwrap
import threading
import unittest.mock
from typing import Any

import pytest

import solara
import solara.server.settings
import solara.settings
import solara.toestand as toestand
import solara.server.kernel_context as kernel_context
from solara.server import kernel
from solara.state import FlushOutcome, MemoryStateBackend, decode, encode, session_hmac
from solara.state import derive, persist
from solara.state.derive import PersistKeyError

SCHEMA_TAG = "schema-1"
SESSION_ID = "test-session"


@pytest.fixture(autouse=True)
def state_env(monkeypatch):
    monkeypatch.setattr(solara.server.settings.state, "secret_keys", "unit-test-secret-key")
    derive._reset_registry()
    persist._reset_registry()
    yield
    derive._reset_registry()
    persist._reset_registry()


_module_counter = itertools.count()


@pytest.fixture
def make_module(tmp_path, monkeypatch):
    # `executing` needs real source on disk, so definition-site tests import generated modules
    monkeypatch.syspath_prepend(str(tmp_path))
    created = []

    def make(body: str):
        name = f"_persist_gen_mod_{next(_module_counter)}"
        (tmp_path / (name + ".py")).write_text(textwrap.dedent(body).lstrip("\n"))
        created.append(name)
        return importlib.import_module(name)

    yield make
    for name in created:
        sys.modules.pop(name, None)


def storage_key_of(reactive: solara.Reactive) -> str:
    storage = reactive._storage
    kernel_store = storage if isinstance(storage, toestand.KernelStore) else getattr(storage, "_storage", None)
    assert isinstance(kernel_store, toestand.KernelStore)
    return kernel_store.storage_key


def make_context(id: str, session_id: str = SESSION_ID) -> kernel_context.VirtualKernelContext:
    return kernel_context.VirtualKernelContext(id=id, kernel=kernel.Kernel(), session_id=session_id)


def fresh_manager(context, backend, envelopes=None, generation=None) -> persist.KernelStatePersistence:
    """Attach a manager the way the server will in commit 2: takeover, then attach."""
    shmac = session_hmac(context.session_id)
    if generation is None:
        result = backend.takeover(context.id, shmac, SCHEMA_TAG)
        generation = result.generation
        if envelopes is None:
            envelopes = result.fields
    return persist.attach(
        context,
        backend,
        session_hmac=shmac,
        schema_tag=SCHEMA_TAG,
        generation=generation,
        envelopes=envelopes or {},
        ttl=60.0,
    )


# --- key resolution -----------------------------------------------------------------------


def test_derived_key_module_level(make_module):
    mod = make_module(
        """
        import solara

        count = solara.reactive(0, persist=True)
        """
    )
    key = f"{mod.__name__}:count"
    assert storage_key_of(mod.count) == key
    registry = persist.persisted_reactives()
    assert key in registry
    config, ref = registry[key]
    assert ref() is mod.count
    assert config.serializer == "json"


def test_explicit_key_wins():
    # key= parameter
    r1 = solara.reactive(0, persist=True, key="explicit.param")
    assert storage_key_of(r1) == "explicit.param"
    # PersistConfig.key
    r2 = solara.reactive(0, persist=solara.PersistConfig(key="explicit.config"))
    assert storage_key_of(r2) == "explicit.config"
    # key= parameter beats PersistConfig.key
    r3 = solara.reactive(0, key="explicit.param2", persist=solara.PersistConfig(key="explicit.ignored"))
    assert storage_key_of(r3) == "explicit.param2"
    registry = persist.persisted_reactives()
    assert set(registry) == {"explicit.param", "explicit.config", "explicit.param2"}


def test_persist_in_factory_raises():
    def factory():
        return solara.reactive("", persist=True)

    with pytest.raises(PersistKeyError) as exc:
        factory()
    assert "key=" in str(exc.value)
    assert persist.persisted_reactives() == {}


def test_explicit_key_collision():
    r1 = solara.reactive(0, persist=True, key="dup.key")
    assert storage_key_of(r1) == "dup.key"
    with pytest.raises(PersistKeyError) as exc:
        solara.reactive(1, persist=True, key="dup.key")
    assert "already used" in str(exc.value)


def test_class_attribute_key(make_module):
    mod = make_module(
        """
        import solara

        class Owner:
            attr = solara.reactive(0, persist=True)
        """
    )
    key = f"{mod.__name__}:Owner.attr"
    assert storage_key_of(mod.Owner.attr) == key
    registry = persist.persisted_reactives()
    assert key in registry
    assert registry[key][1]() is mod.Owner.attr


def test_pending_class_body_without_set_name_fails_loudly_on_attach(make_module):
    # a reactive created with persist=True in a class body, but never assigned to a class
    # attribute, gets no __set_name__ call: creating it works (pending), but the first
    # persistence use (attach) must fail loudly instead of silently never persisting
    mod = make_module(
        """
        import solara

        class Holder:
            stash = {"r": solara.reactive(0, persist=True)}
        """
    )
    assert mod.Holder.stash["r"]._persist_pending
    backend = MemoryStateBackend()
    context = make_context("pending-kernel")
    with pytest.raises(PersistKeyError) as exc:
        fresh_manager(context, backend)
    assert "class body" in str(exc.value)


# --- restore ------------------------------------------------------------------------------


@pytest.mark.parametrize("mutation_detection", [False, True])
def test_restore_skips_default(monkeypatch, mutation_detection):
    monkeypatch.setattr(solara.settings.storage, "mutation_detection", mutation_detection)
    key = "test.restore"
    r = solara.reactive({"a": 1}, persist=True, key=key)
    backend = MemoryStateBackend()
    kernel_id = "restore-kernel"
    field_name = persist.FIELD_PREFIX + key
    envelopes = {field_name: encode({"a": 42}, kernel_id=kernel_id, field_name=field_name)}
    context = make_context(kernel_id)
    manager = fresh_manager(context, backend, envelopes=envelopes, generation=1)
    assert not manager.recovery_failed
    with context:
        # first read installs the restored value instead of the default, without firing
        # listeners and without marking dirty
        assert r.value == {"a": 42}
    assert manager.dirty_keys == set()
    # the restored entry is consumed
    assert manager.restored == {}
    if mutation_detection:
        # the restored value was reconstructed as a StoreValue wrapper: in-place mutation
        # of the public value must still be detected
        with context:
            value = r.value
            value["a"] = 99
            with pytest.raises(ValueError, match="mutated"):
                r.value


def test_bailout_all_or_nothing():
    key1 = "test.bail.one"
    key2 = "test.bail.two"
    r1 = solara.reactive(10, persist=True, key=key1)
    r2 = solara.reactive(20, persist=True, key=key2)
    backend = MemoryStateBackend()
    kernel_id = "bail-kernel"
    shmac = session_hmac(SESSION_ID)
    field1 = persist.FIELD_PREFIX + key1
    field2 = persist.FIELD_PREFIX + key2
    fields = {
        field1: encode(11, kernel_id=kernel_id, field_name=field1),
        field2: encode(22, kernel_id=kernel_id, field_name=field2),
    }
    assert backend.flush(kernel_id, 1, fields, 60.0, shmac, SCHEMA_TAG)
    result = backend.takeover(kernel_id, shmac, SCHEMA_TAG)
    assert result.reason == "restored"
    envelopes = dict(result.fields)
    # tamper with one envelope (flip a MAC bit)
    blob = envelopes[field2]
    envelopes[field2] = blob[:-1] + bytes([blob[-1] ^ 1])
    context = make_context(kernel_id)
    manager = fresh_manager(context, backend, envelopes=envelopes, generation=result.generation)
    # all-or-nothing: nothing restored, cause recorded, poisoned hash deleted
    assert manager.recovery_failed
    assert manager.failed_key == key2
    assert manager.cause == "hmac"
    assert manager.restored == {}
    with context:
        assert r1.value == 10
        assert r2.value == 20
    assert backend.peek_generation(kernel_id) is None


# --- dirty-tracking -----------------------------------------------------------------------


def test_dirty_marking_is_per_context():
    key = "test.dirty"
    r = solara.reactive(0, persist=True, key=key)
    backend = MemoryStateBackend()
    context_a = make_context("dirty-kernel-a")
    context_b = make_context("dirty-kernel-b")
    manager_a = fresh_manager(context_a, backend)
    manager_b = fresh_manager(context_b, backend)
    with context_a:
        r.value = 5
    assert manager_a.dirty_keys == {key}
    assert manager_b.dirty_keys == set()
    # drain via a successful flush
    assert manager_a.flush_now() == FlushOutcome.OK
    assert manager_a.dirty_keys == set()
    # a no-op set (equals) does not mark dirty
    with context_a:
        r.value = 5
    assert manager_a.dirty_keys == set()
    assert manager_b.dirty_keys == set()


def test_ref_field_set_dirties_root_key():
    @dataclasses.dataclass(frozen=True)
    class Form:
        count: int = 0
        name: str = "x"

    key = "test.form"
    r = solara.reactive(Form(), persist=True, key=key)
    backend = MemoryStateBackend()
    context = make_context("ref-kernel")
    manager = fresh_manager(context, backend)
    with context:
        toestand.Ref(r.fields.count).set(3)
        assert r.value.count == 3
    assert manager.dirty_keys == {key}


# --- flush --------------------------------------------------------------------------------


def test_flush_roundtrip_failover_loop():
    key = "test.roundtrip"
    r = solara.reactive("initial", persist=True, key=key)
    backend = MemoryStateBackend()
    kernel_id = "failover-kernel"
    field_name = persist.FIELD_PREFIX + key

    # instance A: fresh takeover (miss), write, flush
    context_a = make_context(kernel_id)
    shmac = session_hmac(SESSION_ID)
    result_a = backend.takeover(kernel_id, shmac, SCHEMA_TAG)
    assert result_a.reason == "miss"
    assert result_a.generation == 1
    manager_a = fresh_manager(context_a, backend, envelopes=result_a.fields, generation=result_a.generation)
    with context_a:
        r.value = "hello from instance A"
    assert manager_a.dirty_keys == {key}
    assert manager_a.flush_now() == FlushOutcome.OK
    assert manager_a.dirty_keys == set()

    # instance B: takeover bumps the generation and reads the envelopes
    result_b = backend.takeover(kernel_id, shmac, SCHEMA_TAG)
    assert result_b.reason == "restored"
    assert result_b.generation == 2
    context_b = make_context(kernel_id)
    manager_b = fresh_manager(context_b, backend, envelopes=result_b.fields, generation=result_b.generation)
    assert not manager_b.recovery_failed
    with context_b:
        assert r.value == "hello from instance A"

    # instance A is now fenced out: its flush is rejected and its keys stay dirty
    with context_a:
        r.value = "stale write from instance A"
    assert manager_a.flush_now() == FlushOutcome.REJECTED
    assert key in manager_a.dirty_keys

    # instance B keeps working; close() does a best-effort final flush (wired via on_close)
    with context_b:
        r.value = "goodbye"
    context_b.on_close(manager_b.close)
    context_b.close()
    result_c = backend.takeover(kernel_id, shmac, SCHEMA_TAG)
    assert result_c.reason == "restored"
    assert decode(result_c.fields[field_name], kernel_id=kernel_id, field_name=field_name) == "goodbye"


def test_keys_stay_dirty_until_ack():
    key = "test.ack"
    r = solara.reactive(0, persist=True, key=key)
    backend = MemoryStateBackend()
    context = make_context("ack-kernel")
    manager = fresh_manager(context, backend)
    with context:
        r.value = 1
    assert manager.dirty_keys == {key}
    # fenced rejection: dirty set unchanged, reported as REJECTED (not a backend-health error)
    with unittest.mock.patch.object(backend, "flush", return_value=False):
        assert manager.flush_now() == FlushOutcome.REJECTED
    assert manager.dirty_keys == {key}
    # backend exception: dirty set unchanged, reported as ERROR (feeds the breaker)
    with unittest.mock.patch.object(backend, "flush", side_effect=RuntimeError("backend down")):
        assert manager.flush_now() == FlushOutcome.ERROR
    assert manager.dirty_keys == {key}
    # ACKed write: cleared
    assert manager.flush_now() == FlushOutcome.OK
    assert manager.dirty_keys == set()
    assert backend.peek_generation(context.id) == 1


def test_serialize_failure_disables_persistence():
    key = "test.unserializable"
    r: solara.Reactive[Any] = solara.reactive(None, persist=True, key=key)
    backend = MemoryStateBackend()
    context = make_context("serialize-kernel")
    manager = fresh_manager(context, backend)
    # make sure a hash exists, so we can observe its deletion
    with context:
        r.value = 1
    assert manager.flush_now() == FlushOutcome.OK
    assert backend.peek_generation(context.id) == 1
    # an unserializable value reaches the opted-in reactive
    with context:
        r.value = lambda: 1  # noqa: E731
    assert manager.dirty_keys == {key}
    assert manager.flush_now() == FlushOutcome.DISABLED
    assert manager.disabled
    # no false confidence: the stored (stale) state is deleted
    assert backend.peek_generation(context.id) is None
    # the app keeps working: sets and flushes do not raise
    with context:
        r.value = 42
        assert r.value == 42
    assert manager.flush_now() == FlushOutcome.DISABLED


def test_snapshot_under_concurrent_mutation_smoke():
    key = "test.concurrent"
    r = solara.reactive({"count": 0}, persist=True, key=key)
    backend = MemoryStateBackend()
    context = make_context("concurrent-kernel")
    manager = fresh_manager(context, backend)
    stop = threading.Event()
    errors = []

    def mutate():
        try:
            with context:
                i = 0
                while not stop.is_set():
                    i += 1
                    # in-place mutation under the reactive's lock (the lock flush snapshots under)
                    with r.lock:
                        r.peek()["count"] = i
                    # and a real set (fires listeners, marks dirty)
                    r.value = {"count": i, "extra": i}
        except Exception as exception:  # noqa
            errors.append(exception)

    thread = threading.Thread(target=mutate)
    thread.start()
    try:
        for _ in range(50):
            manager.flush_now()
    finally:
        stop.set()
        thread.join()
    assert errors == []
    # a final flush drains whatever is left
    assert manager.flush_now() in (FlushOutcome.OK, FlushOutcome.NOTHING)


# --- zero overhead ------------------------------------------------------------------------


def test_zero_overhead_without_persist(monkeypatch):
    def boom():
        raise AssertionError("derive_key must not be called for non-persisted reactives")

    monkeypatch.setattr(derive, "derive_key", boom)
    r = solara.reactive(1)
    assert r.value == 1
    r.value = 2
    assert r.value == 2
    assert persist.persisted_reactives() == {}


def test_none_default_pydantic_model_full_failover_loop():
    # THE motivating case for self-describing tags: an Optional[Model] reactive starting as
    # None - no class is known at definition time, the envelope carries it once a model
    # lands in the reactive. Full loop: set on kernel A, flush, takeover + restore on B.
    import pydantic

    class Profile(pydantic.BaseModel):
        name: str
        age: int

    # the class must be resolvable by module:qualname on the decoding side; a local class
    # is not - promote it to module level for the test
    import sys

    Profile.__qualname__ = "Profile"
    setattr(sys.modules[__name__], "Profile", Profile)
    Profile.__module__ = __name__

    key = "test.optional_profile"
    r: solara.Reactive[Any] = solara.reactive(None, persist=True, key=key)
    backend = MemoryStateBackend()
    context_a = make_context("pydantic-kernel")
    manager_a = fresh_manager(context_a, backend)
    with context_a:
        r.value = Profile(name="ada", age=36)
    assert manager_a.flush_now() == FlushOutcome.OK

    context_b = make_context("pydantic-kernel")
    manager_b = fresh_manager(context_b, backend)
    assert not manager_b.recovery_failed
    with context_b:
        restored = r.value
    assert isinstance(restored, Profile)
    assert restored == Profile(name="ada", age=36)
