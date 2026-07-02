"""Tests for the sync-volume metrics (per persisted key + per kernel, design §7a).

Covers: exact byte accounting against the real envelope encoder, ACK-only recording
(rejections and backend errors record nothing), top-N ordering with the verbose widening
(10 vs 100), the table cap with the "(other)" overflow bucket, kernel-id truncation, and
restore-byte accounting through the real manager attach path.
"""

import pytest

import solara
import solara.server.settings
import solara.server.kernel_context as kernel_context
from solara.server import kernel
from solara.state import MemoryStateBackend, encode, session_hmac
from solara.state import derive, persist
from solara.state.stats import SYNC_TABLE_CAP, stats

SCHEMA_TAG = "schema-1"
SESSION_ID = "test-session"


@pytest.fixture(autouse=True)
def state_env(monkeypatch):
    monkeypatch.setattr(solara.server.settings.state, "secret_keys", "unit-test-secret-key")
    derive._reset_registry()
    persist._reset_registry()
    stats()._reset()
    yield
    derive._reset_registry()
    persist._reset_registry()
    stats()._reset()


def make_context(id: str) -> kernel_context.VirtualKernelContext:
    return kernel_context.VirtualKernelContext(id=id, kernel=kernel.Kernel(), session_id=SESSION_ID)


def make_manager(context, backend) -> persist.KernelStatePersistence:
    shmac = session_hmac(context.session_id)
    result = backend.takeover(context.id, shmac, SCHEMA_TAG)
    return persist.attach(
        context,
        backend,
        session_hmac=shmac,
        schema_tag=SCHEMA_TAG,
        generation=result.generation,
        envelopes=result.fields,
        ttl=60.0,
    )


def test_sync_bytes_match_envelope_sizes():
    r1 = solara.reactive(0, persist=True, key="sync.small")
    r2 = solara.reactive("x", persist=True, key="sync.large")
    backend = MemoryStateBackend()
    context = make_context("sync-kernel-1")
    manager = make_manager(context, backend)
    with context:
        r1.value = 7
        r2.value = "y" * 500
    assert manager.flush_now() == persist.FlushOutcome.OK
    # byte accounting must match the real encoder output exactly
    expected_small = len(encode(7, codec="json", kernel_id=context.id, field_name=persist.FIELD_PREFIX + "sync.small"))
    expected_large = len(encode("y" * 500, codec="json", kernel_id=context.id, field_name=persist.FIELD_PREFIX + "sync.large"))
    d = stats().as_dict()
    assert d["sync_count"] == 2
    assert d["sync_bytes_total"] == expected_small + expected_large
    assert d["sync_mb_total"] == round((expected_small + expected_large) / 1e6, 3)
    by_key = {row["key"]: row for row in d["sync_by_key"]}
    assert by_key["sync.small"]["bytes"] == expected_small
    assert by_key["sync.small"]["syncs"] == 1
    assert by_key["sync.large"]["bytes"] == expected_large
    assert by_key["sync.large"]["bytes_per_sync"] == expected_large
    # ordering: largest first
    assert d["sync_by_key"][0]["key"] == "sync.large"
    # per-kernel ("per user") table: one kernel, both fields summed, id truncated to 8 chars
    assert len(d["sync_by_kernel"]) == 1
    row = d["sync_by_kernel"][0]
    assert row["kernel"] == context.id[:8]
    assert row["syncs"] == 2
    assert row["bytes"] == expected_small + expected_large


def test_rejected_and_errored_flushes_record_nothing(monkeypatch):
    r = solara.reactive(0, persist=True, key="sync.rejected")
    backend = MemoryStateBackend()
    context = make_context("sync-kernel-2")
    manager = make_manager(context, backend)
    with context:
        r.value = 1
    monkeypatch.setattr(backend, "flush", lambda *a, **kw: False)
    assert manager.flush_now() == persist.FlushOutcome.REJECTED
    assert stats().as_dict()["sync_count"] == 0

    def raise_flush(*a, **kw):
        raise RuntimeError("backend down")

    monkeypatch.setattr(backend, "flush", raise_flush)
    assert manager.flush_now() == persist.FlushOutcome.ERROR
    d = stats().as_dict()
    assert d["sync_count"] == 0
    assert d["sync_bytes_total"] == 0
    assert d["sync_by_key"] == []


def test_top_n_ordering_and_verbose_widening():
    s = stats()
    # 150 keys with strictly increasing byte sizes; key-149 is the biggest
    for i in range(150):
        s.record_sync("kernel-x", {f"key-{i}": (i + 1) * 10})
    d = s.as_dict()
    assert len(d["sync_by_key"]) == 10
    assert d["sync_by_key"][0]["key"] == "key-149"
    assert d["sync_by_key"][0]["bytes"] == 1500
    verbose = s.as_dict(verbose=True)
    assert len(verbose["sync_by_key"]) == 100
    assert [row["bytes"] for row in verbose["sync_by_key"]] == sorted((i + 1) * 10 for i in range(50, 150))[::-1]


def test_table_cap_overflow_goes_to_other_bucket():
    s = stats()
    for i in range(SYNC_TABLE_CAP):
        s.record_sync("kernel-y", {f"cap-key-{i}": 1})
    # the cap is reached; two more NEW keys aggregate into "(other)"
    s.record_sync("kernel-y", {"cap-overflow-1": 100})
    s.record_sync("kernel-y", {"cap-overflow-2": 200})
    # an EXISTING key keeps accumulating normally
    s.record_sync("kernel-y", {"cap-key-0": 5})
    d = s.as_dict(verbose=True)
    assert d["sync_keys_dropped"] == 2
    by_key = {row["key"]: row for row in d["sync_by_key"]}
    assert by_key["(other)"]["bytes"] == 300
    assert by_key["(other)"]["syncs"] == 2
    # totals still include everything
    assert d["sync_bytes_total"] == SYNC_TABLE_CAP * 1 + 300 + 5
    # per-kernel table unaffected by the key cap (single kernel)
    assert d["sync_kernels_dropped"] == 0


def test_multiple_kernels_aggregate_per_key():
    key = "shared.filter"
    r = solara.reactive(0, persist=True, key=key)
    backend = MemoryStateBackend()
    sizes = []
    for kid in ("kernel-a-000000", "kernel-b-111111"):
        context = make_context(kid)
        manager = make_manager(context, backend)
        with context:
            r.value = 42
        assert manager.flush_now() == persist.FlushOutcome.OK
        sizes.append(len(encode(42, codec="json", kernel_id=kid, field_name=persist.FIELD_PREFIX + key)))
    d = stats().as_dict()
    by_key = {row["key"]: row for row in d["sync_by_key"]}
    # the VARIABLE aggregates across kernels; the kernels stay separate rows
    assert by_key[key]["syncs"] == 2
    assert by_key[key]["bytes"] == sum(sizes)
    kernels = {row["kernel"] for row in d["sync_by_kernel"]}
    assert kernels == {"kernel-a", "kernel-b"}


def test_restore_bytes_recorded_on_successful_takeover():
    r = solara.reactive(0, persist=True, key="sync.restore")
    backend = MemoryStateBackend()
    context_a = make_context("restore-kernel-a")
    manager_a = make_manager(context_a, backend)
    with context_a:
        r.value = 1234
    assert manager_a.flush_now() == persist.FlushOutcome.OK
    flushed_bytes = stats().as_dict()["sync_bytes_total"]
    assert stats().as_dict()["restore_bytes_total"] == 0
    # a second kernel takes over and restores: the same envelope bytes are read back
    context_b = make_context("restore-kernel-a")
    manager_b = make_manager(context_b, backend)
    assert not manager_b.recovery_failed
    assert manager_b.n_restored == 1
    assert stats().as_dict()["restore_bytes_total"] == flushed_bytes
