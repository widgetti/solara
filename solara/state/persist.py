"""Opt-in reactive state persistence: per-variable config, the process-global persist
registry, and the per-kernel persistence manager.

Three pieces live here (design ``docs/design-redis-state-persistence.md`` §4):

- :class:`PersistConfig` — the two-field per-variable configuration
  (``solara.reactive(..., persist=PersistConfig(key=..., serializer=...))``).
- The process-global persist registry, mapping ``storage_key -> (PersistConfig,
  weakref-to-public-Reactive)`` (§4.4: flush must ``peek()`` the *public* store so
  values are unwrapped from the mutation-detection ``StoreValue`` wrapper).
- :class:`KernelStatePersistence` — one per :class:`VirtualKernelContext`, created by
  :func:`attach` after a backend ``takeover``. It eagerly verifies and decodes all
  restored envelopes (all-or-nothing bail-out, §4.3), lazily installs them at the
  ``KernelStore.get()`` init seam (:meth:`KernelStatePersistence.pop_restored`),
  dirty-marks via ``subscribe_change`` (§4.4, no I/O in listeners), and writes fenced
  batches through :meth:`KernelStatePersistence.flush_now` (§5.3; keys stay dirty until
  the write is ACKed). The debounced write-behind worker and the server wiring that
  calls :func:`attach` land in commit 2.
"""

import copy
import dataclasses
import enum
import logging
import threading
import weakref
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Set, Tuple

import solara.settings
import solara.util

from . import derive
from .backend import StateBackend
from .envelope import EnvelopeError, HmacError, decode, encode
from .stats import log_flush, log_restore, stats

if TYPE_CHECKING:
    from solara.server.kernel_context import VirtualKernelContext
    from solara.toestand import Reactive

logger = logging.getLogger("solara.state")

__all__ = [
    "PersistConfig",
    "KernelStatePersistence",
    "FlushOutcome",
    "attach",
    "FIELD_PREFIX",
    "register_persisted_reactive",
    "persisted_reactives",
]


class FlushOutcome(str, enum.Enum):
    """The result of :meth:`KernelStatePersistence.flush_now`.

    Split so the write-behind worker can route each outcome correctly (design §5.3/§5.5):
    a fenced rejection feeds the *rejection protocol*, a backend error feeds the *circuit
    breaker*, and a serialize failure disables persistence (§4.3) - conflating them (the
    commit-1 ``bool``) hid that distinction.
    """

    OK = "ok"  # the fenced write was acked
    NOTHING = "nothing"  # nothing was dirty (or persistence disabled and nothing to do)
    REJECTED = "rejected"  # the backend fenced us out (another instance owns the generation)
    ERROR = "error"  # the backend call raised (feeds the breaker)
    DISABLED = "disabled"  # a serialize failure disabled persistence for this kernel (§4.3)


# backend hash fields for reactives are namespaced (user_dicts is shared with solara.scope,
# and future namespaces - e.g. session storage - must not collide with reactive keys)
FIELD_PREFIX = "reactive:"


@dataclasses.dataclass
class PersistConfig:
    """Per-variable persistence configuration for `solara.reactive(..., persist=...)`.

    Deliberately two fields in v1:

    - `key`: the stable cross-process persistence key. When None, the key is derived
      from the definition site (module-level single-name assignment or class attribute);
      anything ambiguous raises, demanding an explicit key.
    - `serializer`: the envelope codec name, `"json"` (default, strict with type
      coercion) or `"pickle"` (requires the deployer-side SOLARA_STATE_ALLOW_PICKLE gate).
    """

    key: Optional[str] = None
    serializer: str = "json"


# --- process-global persist registry ------------------------------------------------------
#
# storage_key -> (PersistConfig, weakref to the public Reactive). Weak references: module
# reloads (hot reload) must not keep old reactives alive, and dead entries are re-registerable.

_registry_lock = threading.Lock()
_persist_registry: Dict[str, Tuple[PersistConfig, "weakref.ref"]] = {}
# reactives created with persist=True in a class body, waiting for __set_name__ to resolve
# their key; each entry is (weakref-to-reactive, definition site). If __set_name__ never
# comes (e.g. the reactive was stored inside a dict in the class body), the first
# persistence use (attach) fails loudly.
_pending: List[Tuple["weakref.ref", Tuple[str, int, int]]] = []

# live per-kernel managers (weakly held): a persisted reactive lazily imported *after* a
# manager attached must still get dirty-tracked, so register notifies every attached manager
# to watch it (commit-1 gap: watch-on-late-registration).
_managers_lock = threading.Lock()
_attached_managers: "weakref.WeakSet[KernelStatePersistence]" = weakref.WeakSet()


def register_persisted_reactive(key: str, config: PersistConfig, reactive: "Reactive", source: Tuple[str, int, int], derived: bool) -> None:
    """Register a persisted reactive under its resolved storage key.

    Runs the collision check (two live reactives from different definition sites must not
    share a key), records the public reactive for restore/flush, and - for a reactive
    imported after a kernel already attached - subscribes the live managers so its writes
    are dirty-tracked from now on.
    """
    derive.register_persist_key(key, reactive, source, derived)
    with _registry_lock:
        _persist_registry[key] = (config, weakref.ref(reactive))
    # notify live managers outside _registry_lock: manager.watch enters a kernel context and
    # subscribes a listener, which must not run under the registry lock.
    with _managers_lock:
        managers = list(_attached_managers)
    for manager in managers:
        manager.watch(reactive, key)


def register_pending(reactive: "Reactive", source: Tuple[str, int, int]) -> None:
    """Track a class-body reactive whose key resolution waits for ``__set_name__``."""
    with _registry_lock:
        _pending.append((weakref.ref(reactive), source))


def resolve_pending(reactive: "Reactive", key: str, config: PersistConfig, source: Tuple[str, int, int]) -> None:
    """Complete registration of a class-attribute reactive (the ``__set_name__`` path)."""
    with _registry_lock:
        _pending[:] = [(ref, src) for (ref, src) in _pending if ref() is not None and ref() is not reactive]
    register_persisted_reactive(key, config, reactive, source, derived=True)


def persisted_reactives() -> Dict[str, Tuple[PersistConfig, "weakref.ref"]]:
    """A snapshot of the persist registry: storage_key -> (config, weakref-to-Reactive)."""
    with _registry_lock:
        return dict(_persist_registry)


def _check_pending_resolved() -> None:
    with _registry_lock:
        stale = [(ref(), source) for (ref, source) in _pending]
    stale = [(obj, source) for (obj, source) in stale if obj is not None]
    if stale:
        sites = ", ".join(f"{source[0]}:{source[1]}" for _obj, source in stale)
        raise derive.PersistKeyError(
            f"{len(stale)} reactive(s) created with persist=True in a class body never received a __set_name__ call "
            f"(defined at: {sites}).\n"
            "persist=True in a class body only works for a plain class attribute (Owner.attr = solara.reactive(..., persist=True)); "
            "a reactive stored inside a container or expression in the class body has no stable name.\n"
            'Give it an explicit key=, e.g.  solara.reactive(..., persist=True, key="myapp.unique_name")'
        )


def _reset_registry() -> None:
    """Clear the persist registry and the pending list (tests only)."""
    with _registry_lock:
        _persist_registry.clear()
        del _pending[:]


def _default_ttl() -> float:
    ttl = solara.settings.state.ttl
    if ttl:
        return solara.util.parse_timedelta(ttl)
    try:
        import solara.server.settings as _server_settings

        return solara.util.parse_timedelta(_server_settings.kernel.cull_timeout)
    except Exception:  # noqa
        return 24 * 3600.0


# --- per-kernel persistence manager -------------------------------------------------------


class KernelStatePersistence:
    """Per-kernel-context persistence manager (one per VirtualKernelContext).

    Created via :func:`attach` after a backend ``takeover``. Restored envelopes are
    verified and decoded eagerly (all-or-nothing: any failure discards everything,
    deletes the poisoned hash, and sets ``recovery_failed``); the decoded raw values are
    installed lazily by ``KernelStore.get()`` through :meth:`pop_restored`. Writes are
    dirty-marked via ``subscribe_change`` (scoped to this kernel context) and flushed as
    one fenced batch by :meth:`flush_now`.
    """

    def __init__(
        self,
        context: "VirtualKernelContext",
        backend: StateBackend,
        *,
        session_hmac: bytes,
        schema_tag: str,
        generation: int,
        envelopes: Dict[str, bytes],
        ttl: Optional[float] = None,
    ):
        self.context = context
        self.kernel_id = context.id
        self.backend = backend
        self.session_hmac = session_hmac
        self.schema_tag = schema_tag
        # the fencing token this instance owns; 0 means no write rights (flush always False)
        self.generation = generation
        self.ttl = _default_ttl() if ttl is None else ttl
        # all-or-nothing bail-out state (design §4.3)
        self.recovery_failed = False
        self.failed_key: Optional[str] = None
        self.cause: Optional[str] = None
        # set on a serialize failure at flush: stop persisting for this kernel (§4.3)
        self.disabled = False
        # the TakeoverResult.reason the server observed ("restored"/"miss"/"schema-reset"); set by
        # attach(). Drives the client-facing last_restore status (§6.4). None until attach runs.
        self.restore_reason: Optional[str] = None
        # number of reactive envelopes decoded at takeover; stable even after pop_restored consumes
        # self.restored, so last_restore.nFields stays meaningful once first-render installs values.
        self.n_restored = 0
        # storage_key -> raw (unwrapped) python value, consumed by pop_restored
        self.restored: Dict[str, Any] = {}
        self._dirty_lock = threading.Lock()
        self._dirty: Set[str] = set()
        self._unsubscribers: List[Callable[[], None]] = []
        # storage keys already subscribed, so watch_all + late-registration cannot double-watch
        self._watched: Set[str] = set()
        # set by the flush worker (commit 2); called once when the dirty set goes clean->dirty
        # so a write from any source (task/thread/callback) schedules a debounced flush (§5.3)
        self._flush_scheduler: Optional[Callable[[], None]] = None
        self._decode_envelopes(envelopes)

    def _decode_envelopes(self, envelopes: Dict[str, bytes]) -> None:
        # Eager-decode, lazy-install (§12): verify + decode ALL envelopes now, so a bad
        # envelope is detected before any value is handed out - never a partial restore.
        restored: Dict[str, Any] = {}
        for field_name, blob in envelopes.items():
            if not field_name.startswith(FIELD_PREFIX):
                # not a reactive field (a future namespace); ignore, do not bail out
                continue
            storage_key = field_name[len(FIELD_PREFIX) :]
            try:
                restored[storage_key] = decode(blob, kernel_id=self.kernel_id, field_name=field_name)
            except EnvelopeError as exc:
                cause = "hmac" if isinstance(exc, HmacError) else "codec"
                self.recovery_failed = True
                self.failed_key = storage_key
                self.cause = cause
                stats().incr("restore_bailout")
                log_restore("bailout", kernel=self.kernel_id, key=storage_key, cause=cause)
                logger.debug("bail-out envelope error for kernel %s key %s: %s", self.kernel_id, storage_key, exc)
                # poisoned-hash deletion (§4.3): otherwise every reconnect re-reads the same
                # poisoned envelope and loops in permanent bail-out until TTL
                try:
                    self.backend.delete(self.kernel_id)
                except Exception:  # noqa
                    logger.exception("failed to delete poisoned state for kernel %s", self.kernel_id)
                return
        self.restored = restored
        self.n_restored = len(restored)
        if restored:
            stats().incr("restore_success")
            stats().record_restore_bytes(sum(len(blob) for field_name, blob in envelopes.items() if field_name.startswith(FIELD_PREFIX)))
            log_restore("success", kernel=self.kernel_id)

    @property
    def last_restore(self) -> Dict[str, Any]:
        """Read-only restore outcome for the client (design §6.4 ``lastRestore`` / app-status).

        Maps the takeover reason + eager-decode result to the client-facing vocabulary:
        ``bailout`` (all-or-nothing failure), ``fresh-schema`` (schema-tag reset), ``success``
        (values restored), or ``miss`` (nothing to restore). The ``off`` status is the None-manager
        case, handled by the caller.
        """
        if self.recovery_failed:
            status = "bailout"
        elif self.restore_reason == "schema-reset":
            status = "fresh-schema"
        elif self.n_restored > 0:
            status = "success"
        else:
            status = "miss"
        return {"status": status, "failedKey": self.failed_key, "cause": self.cause, "nFields": self.n_restored}

    # --- restore seam ---------------------------------------------------------------------

    def pop_restored(self, storage_key: str, store: Any) -> Tuple[bool, Any]:
        """Restore-seam hook called by ``KernelStore.get()`` under the per-(variable, kernel)
        init lock, before the default value would be used.

        Returns ``(True, value)`` when a restored value exists for ``storage_key`` - already
        wrapped in a ``StoreValue`` when ``store`` is the inner store of a mutation-detecting
        reactive - else ``(False, None)``. The entry is consumed (popped), so a later
        ``clear()`` lazy-inits from the default again. Must not do I/O, fire listeners, or
        mark dirty (same contract as ``initial_value`` - it runs under init locks).
        """
        if not self.restored:
            return False, None
        try:
            raw = self.restored.pop(storage_key)
        except KeyError:
            return False, None
        from solara._stores import StoreValue, _PublicValueNotSet, _SetValueNotSet

        if isinstance(getattr(store, "default_value", None), StoreValue):
            # mutation detection is on: the stored object must be a StoreValue wrapper, built
            # exactly the way mutation_detection_storage builds one from a raw value (the
            # detector deepcopies private -> public on first read and compares them later)
            wrapped = StoreValue(
                private=copy.deepcopy(raw),
                public=_PublicValueNotSet(),
                get_traceback=None,
                set_value=_SetValueNotSet(),
                set_traceback=None,
            )
            return True, wrapped
        return True, raw

    # --- dirty-tracking -------------------------------------------------------------------

    def watch_all(self) -> None:
        """Subscribe dirty-marking listeners for every registered persisted reactive.

        Listeners are scoped to this manager's kernel context (``subscribe_change`` captures
        the current kernel context), so a write in another kernel does not mark this one dirty.
        """
        for storage_key, (_config, ref) in persisted_reactives().items():
            reactive = ref()
            if reactive is None:
                continue
            self.watch(reactive, storage_key)

    def watch(self, reactive: "Reactive", storage_key: str) -> None:
        """Dirty-mark ``storage_key`` on every real change of ``reactive`` in this context.

        ``subscribe_change`` fires after the ``equals`` dedup and hands the unwrapped new
        value; we deliberately do not capture it (flush peeks fresh). NO I/O here, ever.
        Idempotent per key, so ``watch_all`` and late-registration cannot double-subscribe.
        """
        with self._dirty_lock:
            if storage_key in self._watched:
                return
            self._watched.add(storage_key)

        def _mark_dirty(_new: Any, _old: Any, storage_key: str = storage_key) -> None:
            with self._dirty_lock:
                was_clean = not self._dirty
                self._dirty.add(storage_key)
            # schedule the debounced flush on the clean->dirty edge, outside the dirty lock
            # (the worker takes its own lock); no I/O here, just an alarm-arm.
            if was_clean:
                scheduler = self._flush_scheduler
                if scheduler is not None:
                    scheduler()

        with self.context:
            self._unsubscribers.append(reactive.subscribe_change(_mark_dirty))

    def set_flush_scheduler(self, scheduler: Optional[Callable[[], None]]) -> None:
        """Install (or clear) the callback the write-behind worker arms on the clean->dirty edge."""
        self._flush_scheduler = scheduler

    def mark_all_dirty(self) -> None:
        """Mark every registered persisted key dirty (the rejection-protocol re-flush, §5.5)."""
        keys = set(persisted_reactives().keys())
        if not keys:
            return
        with self._dirty_lock:
            self._dirty |= keys

    @property
    def dirty_keys(self) -> Set[str]:
        """A snapshot of the storage keys with unflushed changes."""
        with self._dirty_lock:
            return set(self._dirty)

    # --- flush ------------------------------------------------------------------------------

    def flush_now(self) -> FlushOutcome:
        """Drain the dirty set and write one fenced batch to the backend.

        Snapshot (deepcopy) under the reactive's lock inside the kernel context; serialize
        and write outside all locks. On a fenced rejection or backend error the drained keys
        are re-marked dirty (keys stay dirty until the write is ACKed, §4.4). A serialize
        failure follows §4.3: log once, delete the kernel's hash, and disable persistence for
        this kernel.

        Returns a :class:`FlushOutcome` so the worker can route the result (a rejection feeds
        the rejection protocol, an error feeds the breaker; §5.3/§5.5). This method is
        breaker-agnostic - the caller checks ``breaker.allow()`` before invoking it. It enters
        the kernel context itself for the snapshot phase (the ONE owner of that step); it never
        holds ``context.lock`` and does the backend I/O outside every lock.
        """
        if self.disabled:
            return FlushOutcome.DISABLED
        with self._dirty_lock:
            drained = set(self._dirty)
            self._dirty.clear()
        if not drained:
            return FlushOutcome.NOTHING
        registry = persisted_reactives()
        snapshots: Dict[str, Tuple[PersistConfig, Any]] = {}
        # enter the kernel context: a context-less thread would resolve reactives to the
        # global scope and snapshot defaults (§5.3)
        with self.context:
            for storage_key in sorted(drained):
                entry = registry.get(storage_key)
                if entry is None:
                    continue
                config, ref = entry
                reactive = ref()
                if reactive is None:
                    continue
                # peek() the PUBLIC reactive (unwraps StoreValue); deepcopy under its lock so
                # a concurrent task cannot hand us a torn snapshot; serialize off-lock below
                try:
                    lock: Optional[Any] = reactive.lock
                except NotImplementedError:
                    lock = None
                with lock if lock is not None else solara.util.nullcontext():
                    snapshots[storage_key] = (config, copy.deepcopy(reactive.peek()))
        fields: Dict[str, bytes] = {}
        for storage_key, (config, value) in snapshots.items():
            field_name = FIELD_PREFIX + storage_key
            try:
                fields[field_name] = encode(value, codec=config.serializer, kernel_id=self.kernel_id, field_name=field_name)
            except EnvelopeError as exc:
                # §4.3 serialize failure: no false confidence - delete the hash and stop
                # persisting for this kernel; a reconnect then restores nothing (fresh state)
                log_flush("error", kernel=self.kernel_id, n_fields=len(fields))
                logger.error(
                    "serialize failure for kernel %s key %s (%s): disabling persistence and deleting stored state",
                    self.kernel_id,
                    storage_key,
                    exc,
                )
                stats().incr("flush_failures")
                self.disabled = True
                try:
                    self.backend.delete(self.kernel_id)
                except Exception:  # noqa
                    logger.exception("failed to delete state for kernel %s", self.kernel_id)
                return FlushOutcome.DISABLED
        try:
            ok = self.backend.flush(self.kernel_id, self.generation, fields, self.ttl, self.session_hmac, self.schema_tag)
        except Exception:  # noqa
            # a backend error (not a fence rejection): re-mark dirty and report ERROR so the
            # caller can feed the circuit breaker
            with self._dirty_lock:
                self._dirty |= drained
            log_flush("error", kernel=self.kernel_id, n_fields=len(fields))
            logger.exception("backend flush raised for kernel %s", self.kernel_id)
            stats().incr("flush_failures")
            stats().record_backend_error("flush raised")
            return FlushOutcome.ERROR
        if not ok:
            # fenced out: another instance owns the generation. Keys stay dirty until ACK
            # (§4.4); this is NOT a backend-health signal, so it does not feed the breaker.
            with self._dirty_lock:
                self._dirty |= drained
            log_flush("rejected", kernel=self.kernel_id, n_fields=len(fields))
            stats().incr("flush_rejected")
            stats().record_backend_ok()
            return FlushOutcome.REJECTED
        log_flush("ok", kernel=self.kernel_id, n_fields=len(fields))
        stats().incr("flush_ok")
        stats().record_backend_ok()
        # sync-volume accounting, only on ACK: rejected/errored flushes re-mark their keys
        # dirty and would double-count on retry (per persist key + per kernel, §7a)
        stats().record_sync(self.kernel_id, {field_name[len(FIELD_PREFIX) :]: len(blob) for field_name, blob in fields.items()})
        return FlushOutcome.OK

    def close(self) -> None:
        """Best-effort final flush, then unsubscribe and drop references.

        Whoever attaches the manager wires this via ``context.on_close`` (the server in
        commit 2; tests in commit 1).
        """
        try:
            if not self.disabled:
                self.flush_now()
        except Exception:  # noqa
            logger.exception("final state flush failed for kernel %s", self.kernel_id)
        self._flush_scheduler = None
        with _managers_lock:
            _attached_managers.discard(self)
        for unsubscribe in self._unsubscribers:
            try:
                unsubscribe()
            except (KeyError, ValueError):  # already removed
                pass
        del self._unsubscribers[:]
        self._watched.clear()
        self.restored = {}
        if getattr(self.context, "state_persistence", None) is self:
            self.context.state_persistence = None


def attach(
    context: "VirtualKernelContext",
    backend: StateBackend,
    *,
    session_hmac: bytes,
    schema_tag: str,
    generation: int,
    envelopes: Dict[str, bytes],
    ttl: Optional[float] = None,
    restore_reason: Optional[str] = None,
) -> KernelStatePersistence:
    """Create a :class:`KernelStatePersistence` for ``context`` and attach it.

    Called after ``backend.takeover(...)`` with the takeover result's ``generation`` and
    ``fields`` (the server wires this on connect in commit 2; tests call it directly).
    Eagerly verifies and decodes all envelopes (all-or-nothing bail-out on any failure,
    incl. poisoned-hash deletion), stores the manager on ``context.state_persistence``
    (the restore seam in ``KernelStore.get()`` reads it), and subscribes dirty-marking
    listeners for all registered persisted reactives, scoped to this context.

    ``restore_reason`` is the ``TakeoverResult.reason`` the server observed; it drives the
    §7a restore counters that only the takeover outcome knows (``miss``/``schema-reset``).
    The ``success``/``bailout`` counters are bumped by the eager decode.

    The caller is responsible for wiring ``context.on_close(manager.close)`` (or, with the
    write-behind worker, ``context.on_close(lambda: worker.close(timeout))``).
    """
    # a persist=True class-body reactive that never got __set_name__ must fail loudly at the
    # first persistence use, not silently never persist
    _check_pending_resolved()
    stats().incr("restore_attempts")
    manager = KernelStatePersistence(
        context,
        backend,
        session_hmac=session_hmac,
        schema_tag=schema_tag,
        generation=generation,
        envelopes=envelopes,
        ttl=ttl,
    )
    manager.restore_reason = restore_reason
    if restore_reason == "miss":
        stats().incr("restore_miss")
        log_restore("miss", kernel=context.id)
    elif restore_reason == "schema-reset":
        stats().incr("restore_schema_reset")
        log_restore("fresh-schema", kernel=context.id)
    context.state_persistence = manager
    # register before watch_all so a reactive registered concurrently is watched by exactly
    # one path (watch() is idempotent per key, so the overlap cannot double-subscribe)
    with _managers_lock:
        _attached_managers.add(manager)
    manager.watch_all()
    return manager
