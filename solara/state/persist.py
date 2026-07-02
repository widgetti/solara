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
import logging
import threading
import weakref
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Set, Tuple

import solara.settings
import solara.util

from . import derive
from .backend import StateBackend
from .envelope import EnvelopeError, HmacError, decode, encode

if TYPE_CHECKING:
    from solara.server.kernel_context import VirtualKernelContext
    from solara.toestand import Reactive

logger = logging.getLogger("solara.state")

__all__ = [
    "PersistConfig",
    "KernelStatePersistence",
    "attach",
    "FIELD_PREFIX",
    "register_persisted_reactive",
    "persisted_reactives",
]

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


def register_persisted_reactive(key: str, config: PersistConfig, reactive: "Reactive", source: Tuple[str, int, int], derived: bool) -> None:
    """Register a persisted reactive under its resolved storage key.

    Runs the collision check (two live reactives from different definition sites must not
    share a key) and records the public reactive for restore/flush.
    """
    derive.register_persist_key(key, reactive, source, derived)
    with _registry_lock:
        _persist_registry[key] = (config, weakref.ref(reactive))


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
        # storage_key -> raw (unwrapped) python value, consumed by pop_restored
        self.restored: Dict[str, Any] = {}
        self._dirty_lock = threading.Lock()
        self._dirty: Set[str] = set()
        self._unsubscribers: List[Callable[[], None]] = []
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
                logger.error(
                    "solara.state.restore result=bailout kernel=%s key=%s cause=%s error=%s",
                    self.kernel_id,
                    storage_key,
                    cause,
                    exc,
                )
                # poisoned-hash deletion (§4.3): otherwise every reconnect re-reads the same
                # poisoned envelope and loops in permanent bail-out until TTL
                try:
                    self.backend.delete(self.kernel_id)
                except Exception:  # noqa
                    logger.exception("failed to delete poisoned state for kernel %s", self.kernel_id)
                return
        self.restored = restored
        if restored:
            logger.info("solara.state.restore result=success kernel=%s n_fields=%d", self.kernel_id, len(restored))

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
        """

        def _mark_dirty(_new: Any, _old: Any, storage_key: str = storage_key) -> None:
            with self._dirty_lock:
                self._dirty.add(storage_key)

        with self.context:
            self._unsubscribers.append(reactive.subscribe_change(_mark_dirty))

    @property
    def dirty_keys(self) -> Set[str]:
        """A snapshot of the storage keys with unflushed changes."""
        with self._dirty_lock:
            return set(self._dirty)

    # --- flush ------------------------------------------------------------------------------

    def flush_now(self) -> bool:
        """Drain the dirty set and write one fenced batch to the backend.

        Snapshot (deepcopy) under the reactive's lock inside the kernel context; serialize
        and write outside all locks. On a fenced rejection or backend error the drained keys
        are re-marked dirty (keys stay dirty until the write is ACKed, §4.4). A serialize
        failure follows §4.3: log ERROR once, delete the kernel's hash, and disable
        persistence for this kernel. Returns True when there was nothing to do or the write
        was ACKed. The debounced worker (commit 2) drives this method.
        """
        if self.disabled:
            return False
        with self._dirty_lock:
            drained = set(self._dirty)
            self._dirty.clear()
        if not drained:
            return True
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
                logger.error(
                    "solara.state.flush result=error kernel=%s key=%s cause=serialize error=%s"
                    " - disabling persistence for this kernel and deleting its stored state",
                    self.kernel_id,
                    storage_key,
                    exc,
                )
                self.disabled = True
                try:
                    self.backend.delete(self.kernel_id)
                except Exception:  # noqa
                    logger.exception("failed to delete state for kernel %s", self.kernel_id)
                return False
        try:
            ok = self.backend.flush(self.kernel_id, self.generation, fields, self.ttl, self.session_hmac, self.schema_tag)
        except Exception:  # noqa
            logger.exception("solara.state.flush result=error kernel=%s n_fields=%d", self.kernel_id, len(fields))
            ok = False
        if not ok:
            # keys stay dirty until ACK (§4.4): a rejection or error must not silently drop
            # these keys until some unrelated future write
            with self._dirty_lock:
                self._dirty |= drained
            logger.warning("solara.state.flush result=rejected kernel=%s n_fields=%d generation=%d", self.kernel_id, len(fields), self.generation)
            return False
        logger.debug("solara.state.flush result=ok kernel=%s n_fields=%d", self.kernel_id, len(fields))
        return True

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
        for unsubscribe in self._unsubscribers:
            try:
                unsubscribe()
            except (KeyError, ValueError):  # already removed
                pass
        del self._unsubscribers[:]
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
) -> KernelStatePersistence:
    """Create a :class:`KernelStatePersistence` for ``context`` and attach it.

    Called after ``backend.takeover(...)`` with the takeover result's ``generation`` and
    ``fields`` (the server wires this on connect in commit 2; tests call it directly).
    Eagerly verifies and decodes all envelopes (all-or-nothing bail-out on any failure,
    incl. poisoned-hash deletion), stores the manager on ``context.state_persistence``
    (the restore seam in ``KernelStore.get()`` reads it), and subscribes dirty-marking
    listeners for all registered persisted reactives, scoped to this context.

    The caller is responsible for wiring ``context.on_close(manager.close)``.
    """
    # a persist=True class-body reactive that never got __set_name__ must fail loudly at the
    # first persistence use, not silently never persist
    _check_pending_resolved()
    manager = KernelStatePersistence(
        context,
        backend,
        session_hmac=session_hmac,
        schema_tag=schema_tag,
        generation=generation,
        envelopes=envelopes,
        ttl=ttl,
    )
    context.state_persistence = manager
    manager.watch_all()
    return manager
