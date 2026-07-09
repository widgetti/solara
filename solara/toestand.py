import contextlib
import dataclasses
import inspect
import logging
import os
import sys
import threading
import time
import traceback
import weakref
from types import FrameType
import warnings
import copy
from abc import ABC, abstractmethod
from collections import defaultdict
from operator import getitem
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    ContextManager,
    Dict,
    Generic,
    Optional,
    Set,
    Tuple,
    TypeVar,
    Union,
    cast,
    overload,
)

import react_ipywidgets as react
import reacton.core
from solara.util import equals_extra

import solara
import solara.settings
from solara import _using_solara_server
from solara.util import nullcontext

if TYPE_CHECKING:
    from solara.state.persist import PersistConfig

T = TypeVar("T")
TS = TypeVar("TS")
S = TypeVar("S")  # used for state
logger = logging.getLogger("solara.toestand")

_DEBUG = False


class ThreadLocal(threading.local):
    reactive_used: Optional[Set["ValueBase"]] = None
    reactive_watch: Optional[Callable[["ValueBase"], None]] = None
    # True while solara-internal machinery subscribes: those owners guarantee cleanup,
    # so the subscription-leak warning must not fire for them
    managed_subscribe: bool = False


thread_local = ThreadLocal()


@contextlib.contextmanager
def _managed_subscription():
    """Mark subscriptions made in this block as managed (cleanup guaranteed by the caller)."""
    previous = thread_local.managed_subscribe
    thread_local.managed_subscribe = True
    try:
        yield
    finally:
        thread_local.managed_subscribe = previous


@dataclasses.dataclass
class _SubscriptionLeakCheck:
    site: str
    store_name: str
    resolved: bool = False


# per kernel context id: subscriptions to check for leaks when it closes
# (popped by the on_close report; VirtualKernelContext itself is unhashable)
_pending_subscription_checks: Dict[str, list] = {}
_warned_sites: Set[str] = set()
_internal_packages_paths = None


def _warn_once(site: str, message: str):
    if site in _warned_sites:
        return
    _warned_sites.add(site)
    warnings.warn(message, UserWarning, stacklevel=3)


def _app_call_site() -> Optional[str]:
    """file:lineno of the nearest stack frame outside solara/reacton internals."""
    global _internal_packages_paths
    if _internal_packages_paths is None:
        import react_ipywidgets
        import reacton

        _internal_packages_paths = tuple(os.path.dirname(mod.__file__ or "") + os.sep for mod in (solara, reacton, react_ipywidgets))
    frame: Optional[FrameType] = sys._getframe(1)
    while frame is not None:
        filename = frame.f_code.co_filename
        if not filename.startswith(_internal_packages_paths) and "importlib" not in filename:
            return f"{filename}:{frame.f_lineno}"
        frame = frame.f_back
    return None


# these hooks should go into react-ipywidgets
def use_sync_external_store(subscribe: Callable[[Callable[[], None]], Callable[[], None]], get_snapshot: Callable[[], Any]):
    _, set_counter = react.use_state(0)

    def force_update():
        set_counter(lambda x: x + 1)

    state = get_snapshot()
    prev_state = react.use_ref(state)

    def update_state():
        prev_state.current = state

    react.use_effect(update_state)

    def on_store_change(_ignore_new_state=None):
        new_state = get_snapshot()
        if not equals_extra(new_state, prev_state.current):
            prev_state.current = new_state
            force_update()

    def subscribe_managed():
        # effect-managed: reacton guarantees the returned cleanup runs on unmount/close
        with _managed_subscription():
            return subscribe(on_store_change)

    react.use_effect(subscribe_managed, [])
    return state


def use_sync_external_store_with_selector(subscribe, get_snapshot: Callable[[], Any], selector):
    return use_sync_external_store(subscribe, lambda: selector(get_snapshot()))


def merge_state(d1: S, **kwargs) -> S:
    if dataclasses.is_dataclass(d1):
        return dataclasses.replace(d1, **kwargs)  # type: ignore
    if "pydantic" in sys.modules and isinstance(d1, sys.modules["pydantic"].BaseModel):
        module = sys.modules["pydantic"]
        version_major = int(module.__version__.split(".")[0])
        if version_major >= 2:
            return d1.model_copy(update=kwargs)
        else:
            return d1.copy(update=kwargs)
    return cast(S, {**cast(dict, d1), **kwargs})


class ValueBase(Generic[T]):
    def __init__(self, merge: Callable = merge_state, equals=equals_extra):
        self.merge = merge
        self.equals = equals
        self.listeners: Dict[str, Set[Tuple[Callable[[T], None], Optional[ContextManager]]]] = defaultdict(set)
        self.listeners2: Dict[str, Set[Tuple[Callable[[T, T], None], Optional[ContextManager]]]] = defaultdict(set)

    # make sure all boolean operations give type errors
    if not solara.settings.main.allow_reactive_boolean:

        def __bool__(self):
            raise TypeError("Reactive vars are not allowed in boolean expressions, did you mean to use .value?")

        def __eq__(self, other):
            raise TypeError(f"'==' not supported between a Reactive and {other.__class__.__name__}, did you mean to use .value?")

        def __ne__(self, other):
            raise TypeError(f"'!=' not supported between a Reactive and {other.__class__.__name__}, did you mean to use .value?")

        # If we explicitly define __eq__, we need to explicitly define __hash__ as well
        # Otherwise our class is marked unhashable
        __hash__ = object.__hash__

    def __lt__(self, other):
        raise TypeError(f"'<' not supported between a Reactive and {other.__class__.__name__}, did you mean to use .value?")

    def __le__(self, other):
        raise TypeError(f"'<=' not supported between a Reactive and {other.__class__.__name__}, did you mean to use .value?")

    def __gt__(self, other):
        raise TypeError(f"'>' not supported between a Reactive and {other.__class__.__name__}, did you mean to use .value?")

    def __ge__(self, other):
        raise TypeError(f"'>=' not supported between a Reactive and {other.__class__.__name__}, did you mean to use .value?")

    def __len__(self):
        raise TypeError("'len(...)' is not supported for a Reactive, did you mean to use .value?")

    @property
    def lock(self):
        raise NotImplementedError

    def clear(self):
        """Remove the stored value for the current scope (e.g. this kernel).

        No-op for storage without per-scope entries; kernel-scoped stores drop
        this kernel's entry (used by use_task when its component unmounts).
        """
        pass

    @property
    def value(self) -> T:
        return self.get()

    @value.setter
    def value(self, value: T):
        self.set(value)

    def set(self, value: T):
        raise NotImplementedError

    def peek(self) -> T:
        raise NotImplementedError

    def get(self) -> T:
        raise NotImplementedError

    def _get_scope_key(self):
        raise NotImplementedError

    def subscribe(self, listener: Callable[[T], None], scope: Optional[ContextManager] = None):
        if scope is not None:
            warnings.warn("scope argument should not be used, it was only for internal use")
        del scope
        scope_id = self._get_scope_key()
        rc = reacton.core.get_render_context(required=False)
        if _using_solara_server():
            import solara.server.kernel_context

            kernel = solara.server.kernel_context.get_current_context() if solara.server.kernel_context.has_current_context() else nullcontext()
        else:
            kernel = nullcontext()
        context = Context(rc, kernel)

        self.listeners[scope_id].add((listener, context))
        leak_check = self._track_subscription()

        def cleanup():
            if leak_check is not None:
                leak_check.resolved = True
            entries = self.listeners.get(scope_id)
            if entries is not None:
                entries.discard((listener, context))
                # prune the scope entry itself: unsubscribing must leave no residue,
                # or every kernel that ever subscribed leaves an empty set behind.
                # pop(default), not del: two cleanups for the same scope (concurrent
                # recomputes of two computeds sharing a reactive) can both observe the
                # set empty and both prune — a plain del KeyErrors on the second.
                if not entries:
                    self.listeners.pop(scope_id, None)

        return cleanup

    def subscribe_change(self, listener: Callable[[T, T], None], scope: Optional[ContextManager] = None):
        if scope is not None:
            warnings.warn("scope argument should not be used, it was only for internal use")
        del scope
        scope_id = self._get_scope_key()
        rc = reacton.core.get_render_context(required=False)
        if _using_solara_server():
            import solara.server.kernel_context

            kernel = solara.server.kernel_context.get_current_context() if solara.server.kernel_context.has_current_context() else nullcontext()
        else:
            kernel = nullcontext()
        context = Context(rc, kernel)
        self.listeners2[scope_id].add((listener, context))
        leak_check = self._track_subscription()

        def cleanup():
            if leak_check is not None:
                leak_check.resolved = True
            entries = self.listeners2.get(scope_id)
            if entries is not None:
                entries.discard((listener, context))
                if not entries:
                    self.listeners2.pop(scope_id, None)  # idempotent under concurrent cleanup (see listeners above)

        return cleanup

    def _track_subscription(self) -> Optional[_SubscriptionLeakCheck]:
        """Warn (once per call site) for subscriptions still alive when their kernel closes.

        A subscription made inside a kernel whose cleanup is never called outlives
        the kernel forever on a process-lifetime store: the listeners dict entry pins
        the listener closure and everything it captures (see
        docs/memory-usage-inspection.md, case study 4). Solara's own subscription
        owners (auto-subscribe, use_sync_external_store) always clean up and mark
        themselves with _managed_subscription(); anything else made while a kernel
        context is current gets tracked and reported at kernel close if its cleanup
        never ran.
        """
        if thread_local.managed_subscribe or not _using_solara_server():
            return None
        if reacton.core.get_render_context(required=False) is not None:
            # subscriptions made during a render (component bodies, effects) are
            # component-managed: use_effect cleanups run on unmount and at close
            return None
        import solara.server.kernel_context

        if not solara.server.kernel_context.has_current_context():
            return None
        kernel_context = solara.server.kernel_context.get_current_context()
        if kernel_context.id == "dummy":
            # the app script itself runs in the short-lived dummy context; module-level
            # subscriptions made there are process-lifetime by intent
            return None
        site = _app_call_site()
        if site is None:
            return None
        leak_check = _SubscriptionLeakCheck(site, repr(self))
        checks = _pending_subscription_checks.setdefault(kernel_context.id, [])
        checks.append(leak_check)
        if len(checks) == 1:
            kernel_id = kernel_context.id

            def report():
                for check in _pending_subscription_checks.pop(kernel_id, []):
                    if not check.resolved:
                        _warn_once(
                            check.site,
                            f"A subscription to {check.store_name} made at {check.site} was still active when "
                            "its kernel closed. Store the unsubscribe function returned by "
                            "subscribe()/subscribe_change() and call it (e.g. from a use_effect cleanup), "
                            "otherwise the listener and everything it captures leak for the lifetime of the process.",
                        )

            kernel_context.on_close(report)
        return leak_check

    def fire(self, new: T, old: T):
        logger.info("value change from %s to %s, will fire events", old, new)
        scope_id = self._get_scope_key()
        # .get instead of indexing: these are defaultdicts, and indexing would
        # permanently materialize an empty set for every kernel that ever fires,
        # growing the dicts by one entry per kernel for the process lifetime
        contexts = set()
        for listener, context in tuple(self.listeners.get(scope_id, ())):
            contexts.add(context)
        for listener2, context in tuple(self.listeners2.get(scope_id, ())):
            contexts.add(context)
        if contexts:
            for context in contexts:
                with context or nullcontext():
                    for listener, context_listener in tuple(self.listeners.get(scope_id, ())):
                        if context == context_listener:
                            listener(new)
                    for listener2, context_listener in tuple(self.listeners2.get(scope_id, ())):
                        if context == context_listener:
                            listener2(new, old)

    def update(self, _f=None, **kwargs):
        if _f is not None:
            assert not kwargs
            with self.lock:
                kwargs = _f(self.get())
        with self.lock:
            # important to have this part thread-safe
            new = self.merge(self.get(), **kwargs)
            self.set(new)

    def use_value(self) -> T:
        # .use with the default argument doesn't give good type inference
        return self.use()

    def use(self, selector: Callable[[T], TS] = lambda x: x) -> TS:  # type: ignore
        return selector(self.value)

    def use_state(self) -> Tuple[T, Callable[[T], None]]:
        setter = self.set
        value = self.use()  # type: ignore
        return value, setter

    @property
    def fields(self) -> T:
        # we lie about the return type, but in combination with
        # setter we can make type safe setters (see docs/tests)
        return cast(T, Fields(self))

    def setter(self, field: TS) -> Callable[[TS], None]:
        _field = cast(FieldBase, field)

        def setter(new_value: TS):
            _field.set(new_value)

        return cast(Callable[[TS], None], setter)

    def _check_mutation(self):
        pass


# the default store for now, stores in a global dict, or when in a solara
# context, in the solara user context


class KernelStore(ValueBase[S], ABC):
    _global_dict: Dict[str, S] = {}  # outside of solara context, this is used
    # we keep a counter per type, so the storage keys we generate are deterministic
    _type_counter: Dict[Any, int] = defaultdict(int)
    # guards the shared, class-level _type_counter above; must stay class-level
    # because the counter is shared across all instances
    _type_counter_lock = threading.RLock()

    def __init__(self, key: str, equals: Callable[[Any, Any], bool] = equals_extra):
        super().__init__(equals=equals)
        self.storage_key = key
        self._global_dict = {}
        # since a set can trigger events, which can trigger new updates, we need a recursive lock
        self._lock = threading.RLock()
        # guards lazy initialization of the value in the GLOBAL scope (the per-instance
        # _global_dict). For a kernel scope the lock lives on the kernel context instead, keyed
        # by storage_key (see _scope_init_lock), so the same reactive initializing in different
        # kernels uses different locks and does not serialize.
        self._init_lock = threading.RLock()
        # monotonic time of the last "init lock seems stuck" warning, to throttle logging. This
        # is per-instance (per reactive, shared across kernels) -- intentionally coarser than the
        # lock, to bound log volume.
        self._init_lock_warning_time: Optional[float] = None
        self.local = threading.local()

    @property
    def lock(self):
        return self._lock

    def _get_scope_key(self):
        scope_dict, scope_id, context = self._get_dict()
        return scope_id

    def _get_dict(self):
        # Resolve the scope once: the per-kernel user_dicts (plus the context, whose init_locks we
        # use for locking) when inside a kernel, else the per-instance global dict. Returning the
        # context here -- rather than re-resolving it for the lock -- keeps get()'s dict and lock
        # from ever disagreeing.
        scope_dict = self._global_dict
        scope_id = "global"
        context = None
        if _using_solara_server():
            import solara.server.kernel_context

            try:
                context = solara.server.kernel_context.get_current_context()
            except RuntimeError:  # noqa
                context = None  # no current kernel context -> global scope
            else:
                scope_dict = cast(Dict[str, S], context.user_dicts)
                scope_id = context.id
        return cast(Dict[str, S], scope_dict), scope_id, context

    def peek(self):
        return self.get()

    def get(self):
        scope_dict, scope_id, context = self._get_dict()
        if self.storage_key not in scope_dict:
            # The lock guarding lazy init of THIS reactive in THIS scope. For a kernel scope it
            # lives on the context (keyed by storage_key, created on first access, dying with the
            # context), so the same reactive initializing in different kernels uses different
            # locks. For the global scope it is the per-instance lock.
            lock = self._init_lock if context is None else context.init_locks[self.storage_key]
            with self._init_lock_held(lock, scope_id):
                if self.storage_key not in scope_dict:
                    # we assume immutable, so don't make a copy
                    scope_dict[self.storage_key] = self._restored_or_initial_value(context)
        return scope_dict[self.storage_key]

    def _restored_or_initial_value(self, context) -> S:
        # Restore seam for opt-in state persistence: when this kernel context carries a
        # persistence manager holding a restored value for this key (attached after a backend
        # takeover, see solara.state.persist), install that value instead of the default.
        # Runs under the per-(variable, kernel) init lock: the manager hook does no I/O and
        # fires no listeners, and the restored entry is consumed so a later clear() lazy-inits
        # from the default again. Non-server/global scopes have context None and pay nothing.
        if context is not None and context.state_persistence is not None:
            restored, value = context.state_persistence.pop_restored(self.storage_key, self)
            if restored:
                return cast(S, value)
        return self.initial_value()

    @contextlib.contextmanager
    def _init_lock_held(self, lock: threading.RLock, scope_id: str):
        # Acquire the given lazy-init lock, then release it once initial_value() has run (acquire
        # and release live together so they stay balanced, even when initial_value() raises). A
        # non-positive (or NaN) init_lock_timeout disables the warning and waits indefinitely;
        # otherwise we keep retrying, warning (throttled) when we seem stuck -- which usually means
        # a deadlock or an unusually slow initial value.
        timeout = solara.settings.storage.init_lock_timeout
        if timeout > 0:
            while not lock.acquire(timeout=timeout):
                self._warn_init_lock_timeout(timeout, scope_id)
        else:
            lock.acquire()
        try:
            yield
        finally:
            lock.release()

    def _warn_init_lock_timeout(self, timeout: float, scope_id: str):
        now = time.monotonic()
        cooldown = solara.settings.storage.init_lock_warning_cooldown
        last = self._init_lock_warning_time
        if last is not None and (now - last) < cooldown:
            return
        self._init_lock_warning_time = now
        # Dump every thread's stack so the one stuck inside initial_value() is visible. Building
        # the diagnostic must never break the retry loop, so fall back quietly on any problem.
        try:
            frames = sys._current_frames() if hasattr(sys, "_current_frames") else {}
            stacks = "\n".join(f"Thread {ident}:\n" + "".join(traceback.format_stack(frame)) for ident, frame in frames.items())
        except Exception:  # noqa
            stacks = "<thread stacks unavailable>"
        # error (not warning) is intentional: a multi-second init stall is a real production
        # problem even though we keep retrying and usually recover.
        logger.error(
            "Timed out after %.1fs waiting to initialize reactive variable %r (scope=%r). This usually indicates a "
            "deadlock (an initial value or factory blocking on a lock held by the initializing thread) or an unusually "
            "slow initial value. Still retrying; further warnings for this variable (across all kernels) are suppressed "
            "for %.0fs.\nThread stacks:\n%s",
            timeout,
            self.storage_key,
            scope_id,
            cooldown,
            stacks,
        )

    def clear(self):
        scope_dict, scope_id, context = self._get_dict()
        if self.storage_key in scope_dict:
            del scope_dict[self.storage_key]

    def set(self, value: S):
        scope_dict, scope_id, context = self._get_dict()
        if not solara.settings.main.allow_global_context and scope_id == "global":
            raise RuntimeError(
                f"No kernel context found, and global context is not allowed for task, context key was {solara.server.kernel_context.get_current_thread_key()}"
            )
        old = self.get()
        if self.equals(old, value):
            return
        scope_dict[self.storage_key] = value

        if _DEBUG:
            import traceback

            traceback.print_stack(limit=17, file=sys.stdout)

            print("change old", old)  # noqa
            print("change new", value)  # noqa

        self.fire(value, old)

    @abstractmethod
    def initial_value(self) -> S:
        pass

    def _check_mutation(self):
        pass


def _is_internal_module(file_name: str):
    file_name_parts = file_name.split(os.sep)
    if len(file_name_parts) < 2:
        return False
    return (
        file_name_parts[-2:] == ["solara", "toestand.py"]
        or file_name_parts[-2:] == ["solara", "reactive.py"]
        or file_name_parts[-2:] == ["solara", "tasks.py"]
        or file_name_parts[-2:] == ["solara", "_stores.py"]
        or file_name_parts[-3:] == ["solara", "hooks", "use_reactive.py"]
        or file_name_parts[-2:] == ["reacton", "core.py"]
        # If we use SomeClass[K](...) we go via the typing module, so we need to skip that as well
        or (file_name_parts[-2].startswith("python") and file_name_parts[-1] == "typing.py")
    )


def _find_outside_solara_frame() -> Optional[FrameType]:
    # the module where the call stack origined from
    current_frame: Optional[FrameType] = None
    module_frame = None

    # _getframe is not guaranteed to exist in all Python implementations,
    # but is much faster than the inspect module
    if hasattr(sys, "_getframe"):
        current_frame = sys._getframe(1)
    else:
        current_frame = inspect.currentframe()

    while current_frame is not None:
        file_name = current_frame.f_code.co_filename
        # Skip most common cases, i.e. toestand.py, reactive.py, use_reactive.py, Reacton's core.py, and the typing module
        if not _is_internal_module(file_name):
            module_frame = current_frame
            break
        current_frame = current_frame.f_back

    return module_frame


class KernelStoreValue(KernelStore[S]):
    default_value: S
    _traceback: Optional[inspect.Traceback]
    _default_value_copy: Optional[S]

    def __init__(self, default_value: S, key=None, equals: Callable[[Any, Any], bool] = equals_extra, unwrap=lambda x: x):
        self.default_value = default_value
        self._unwrap = unwrap
        self.equals = equals
        self._mutation_detection = solara.settings.storage.mutation_detection
        if self._mutation_detection:
            frame = _find_outside_solara_frame()
            if frame is not None:
                self._traceback = inspect.getframeinfo(frame)
            else:
                self._traceback = None
            self._default_value_copy = copy.deepcopy(default_value)
            if not self.equals(self._unwrap(self.default_value), self._unwrap(self._default_value_copy)):
                msg = """The equals function for this reactive value returned False when comparing a deepcopy to itself.

This reactive variable will not be able to detect mutations correctly, and is therefore disabled.

To avoid this warning, and to ensure that mutation detection works correctly, please provide a better equals function to the reactive variable.
A good choice for dataframes and numpy arrays might be solara.util.equals_pickle, which will also attempt to compare the pickled values of the objects.

Example:
df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
reactive_df = solara.reactive(df, equals=solara.util.equals_pickle)
"""
                tb = self._traceback
                if tb:
                    if tb.code_context:
                        code = tb.code_context[0]
                    else:
                        code = "<No code context available>"
                    msg += f"This warning was triggered from:\n{tb.filename}:{tb.lineno}\n{code}"
                warnings.warn(msg)
                self._mutation_detection = False
        cls = type(default_value)
        if key is None:
            with KernelStore._type_counter_lock:
                index = self._type_counter[cls]
                self._type_counter[cls] += 1
            key = cls.__module__ + ":" + cls.__name__ + ":" + str(index)
        super().__init__(key=key, equals=equals)

    def initial_value(self) -> S:
        self._check_mutation()
        return self.default_value

    def _check_mutation(self):
        if not self._mutation_detection:
            return
        initial = self._unwrap(self._default_value_copy)
        current = self._unwrap(self.default_value)
        if not self.equals(initial, current):
            tb = self._traceback
            if tb:
                if tb.code_context:
                    code = tb.code_context[0].strip()
                else:
                    code = "No code context available"
                msg = f"Reactive variable was initialized at {tb.filename}:{tb.lineno} with {initial!r}, but was mutated to {current!r}.\n{code}"
            else:
                msg = f"Reactive variable was initialized with a value of {initial!r}, but was mutated to {current!r} (unable to report the location in the source code)."
            raise ValueError(msg)


def _create_key_callable(f: Callable):
    try:
        prefix = f.__qualname__
    except Exception:
        prefix = repr(f)
    with KernelStore._type_counter_lock:
        index = KernelStore._type_counter[prefix]
        KernelStore._type_counter[prefix] += 1
    try:
        key = f.__module__ + ":" + prefix + ":" + str(index)
    except Exception:
        key = prefix + ":" + str(index)
    return key


class KernelStoreFactory(KernelStore[S]):
    def __init__(self, factory: Callable[[], S], key=None, equals: Callable[[Any, Any], bool] = equals_extra):
        self.factory = factory
        key = key or _create_key_callable(factory)
        super().__init__(key=key, equals=equals)

    def initial_value(self) -> S:
        return self.factory()


def mutation_detection_storage(default_value: S, key=None, equals=None) -> ValueBase[S]:
    from solara.util import equals_pickle as default_equals
    from ._stores import MutateDetectorStore, StoreValue, _PublicValueNotSet, _SetValueNotSet

    kernel_store = KernelStoreValue[StoreValue[S]](
        StoreValue[S](private=default_value, public=_PublicValueNotSet(), get_traceback=None, set_value=_SetValueNotSet(), set_traceback=None),
        key=key,
        unwrap=lambda x: x.private,
    )
    return MutateDetectorStore[S](kernel_store, equals=equals or default_equals)


def default_storage(default_value: S, key=None, equals=None) -> ValueBase[S]:
    # in solara v2 we will also do this when mutation_detection is None
    # and we do not run on production mode
    if solara.settings.storage.mutation_detection is True:
        return mutation_detection_storage(default_value, key=key, equals=equals)
    else:
        return KernelStoreValue[S](default_value, key=key, equals=equals or equals_extra)


def _call_storage_factory(default_value: S, key=None, equals=None) -> ValueBase[S]:
    factory = solara.settings.storage.get_factory()
    return factory(default_value, key=key, equals=equals)


class Reactive(ValueBase[S]):
    _storage: ValueBase[S]

    def __init__(self, default_value: Union[S, ValueBase[S]], key=None, equals=None, persist: Union[bool, "PersistConfig"] = False):
        super().__init__()
        self._persist_config: Optional["PersistConfig"] = None
        self._persist_derived = False
        # persist=True in a class body: the key is resolved in __set_name__ (module:Owner.attr)
        self._persist_pending = False
        if persist:
            key = self._init_persist(default_value, key, persist)
        if not isinstance(default_value, ValueBase):
            self._storage = _call_storage_factory(default_value, key=key, equals=equals)
        else:
            self._storage = default_value
        if self._persist_config is not None:
            self._register_persist(key)
        self.__post__init__()
        self._name = None
        self._owner = None

    def _init_persist(self, default_value, key: Optional[str], persist: "Union[bool, PersistConfig]") -> Optional[str]:
        # Resolve the persistence key: explicit key= (or PersistConfig.key) wins; otherwise it
        # is derived from the definition site (raising PersistKeyError on anything ambiguous -
        # that error message is the specified UX). The resolved key becomes the storage_key of
        # the underlying store, so restored state lands on the right variable cross-process.
        from solara.state import derive
        from solara.state.persist import PersistConfig

        if isinstance(default_value, ValueBase):
            raise ValueError("persist= cannot be combined with a custom store, pass a plain default value instead")
        config = PersistConfig() if persist is True else persist
        if not isinstance(config, PersistConfig):
            raise TypeError(f"persist must be True/False or a solara.PersistConfig, not {persist!r}")
        self._persist_config = config
        if key is None:
            key = config.key
        if key is None:
            try:
                key = derive.derive_key()
            except derive.PersistKeyError as exception:
                if getattr(exception, "reason", None) == derive.REASON_CLASS_BODY:
                    # a class attribute: __set_name__ (called when the class body completes)
                    # resolves the key to module:Owner.attr; until then we are pending
                    self._persist_pending = True
                    return None
                raise
            self._persist_derived = True
        return key

    def _register_persist(self, key: Optional[str]) -> None:
        from solara.state import persist as state_persist

        frame = _find_outside_solara_frame()
        source = (frame.f_code.co_filename, frame.f_lineno, 0) if frame is not None else ("<unknown>", 0, 0)
        assert self._persist_config is not None
        if self._persist_pending:
            state_persist.register_pending(self, source)
        else:
            assert key is not None
            state_persist.register_persisted_reactive(key, self._persist_config, self, source, derived=self._persist_derived)

    def __set_name__(self, owner, name):
        self._name = name
        self._owner = owner
        if getattr(self, "_persist_pending", False):
            self._resolve_persist_key_for_class_attribute(owner, name)

    def _resolve_persist_key_for_class_attribute(self, owner, name):
        from solara.state import derive
        from solara.state import persist as state_persist

        key = derive.derive_key_for_class_attribute(owner, name)
        storage = self._storage
        kernel_store = storage if isinstance(storage, KernelStore) else getattr(storage, "_storage", None)
        if not isinstance(kernel_store, KernelStore):
            raise derive.PersistKeyError(
                f"cannot re-key the storage of persisted class attribute {owner.__qualname__}.{name}: "
                f"unsupported storage type {type(storage).__name__}; give an explicit key= instead"
            )
        # Re-key before any kernel use: user_dicts fill lazily and the class body has just
        # finished executing, so nothing can have read this reactive under the temporary key
        # yet (cheaply verifiable only for the global scope).
        assert kernel_store.storage_key not in kernel_store._global_dict, "reactive was read before __set_name__ resolved its persistence key"
        kernel_store.storage_key = key
        self._persist_pending = False
        assert self._persist_config is not None
        frame = _find_outside_solara_frame()
        source = (frame.f_code.co_filename, frame.f_lineno, 0) if frame is not None else ("<unknown>", 0, 0)
        state_persist.resolve_pending(self, key, self._persist_config, source)

    def __repr__(self):
        value = self.peek()
        if self._name:
            return f"<Reactive {self._owner.__name__}.{self._name} value={value!r} id={hex(id(self))}>"
        else:
            return f"<Reactive value={value!r} id={hex(id(self))}>"

    def __str__(self):
        if self._name:
            return f"{self._owner.__name__}.{self._name}={self.value!r}"
        else:
            return f"{self.value!r}"

    @property
    def lock(self):
        return self._storage.lock

    def __post__init__(self):
        pass

    def update(self, *args, **kwargs):
        self._storage.update(*args, **kwargs)

    def set(self, value: S):
        if value is self:
            raise ValueError("Can't set a reactive to itself")
        self._storage.set(value)

    def get(self, add_watch=None) -> S:
        if add_watch is not None:
            warnings.warn("add_watch is deprecated, use .peek()", DeprecationWarning)
        if thread_local.reactive_used is not None:
            thread_local.reactive_used.add(self)
        if thread_local.reactive_watch is not None:
            thread_local.reactive_watch(self)
        # peek to avoid parents also adding themselves to the reactive_used set
        return self._storage.peek()

    def peek(self) -> S:
        """Return the value without automatically subscribing to listeners."""
        return self._storage.peek()

    def subscribe(self, listener: Callable[[S], None], scope: Optional[ContextManager] = None):
        return self._storage.subscribe(listener, scope=scope)

    def subscribe_change(self, listener: Callable[[S, S], None], scope: Optional[ContextManager] = None):
        return self._storage.subscribe_change(listener, scope=scope)

    def computed(self, f: Callable[[S], T]) -> "Computed[T]":
        def func():
            return f(self.get())

        return Computed(func, key=f.__qualname__)


def _on_kernel_start_scoped_to_creator(f: Callable[[], Optional[Callable[[], None]]]) -> Callable[[], None]:
    """on_kernel_start, but scoped to the creating kernel when there is one.

    Module-level Singleton/Computed instances register at import time (no kernel
    context) and live for the process — a process-global registration is right.
    Instances created inside a kernel (a Computed in a component body, use_task's
    Singleton) must not outlive it: unregister when that kernel closes. The
    lifecycle cleanup is idempotent, so an earlier unmount cleanup (use_task) and
    the kernel-close unregistration can both run.

    The app script itself runs inside the short-lived "dummy" kernel context
    (solara.server.app), so module-level instances of an app ARE created inside
    a kernel — scoping to the dummy context would unregister every module-level
    reset the moment startup finishes (and break hot reload). Skip it.
    """
    import solara.lifecycle

    cleanup = solara.lifecycle.on_kernel_start(f)
    if _using_solara_server():
        import solara.server.kernel_context

        if solara.server.kernel_context.has_current_context():
            context = solara.server.kernel_context.get_current_context()
            if context.id != "dummy":
                context.on_close(cleanup)
    return cleanup


class Singleton(Reactive[S]):
    _storage: KernelStore[S]

    def __init__(self, factory: Callable[[], S], key=None):
        super().__init__(KernelStoreFactory(factory, key=key))

        # reset on kernel restart (e.g. hot reload)
        def reset():
            def cleanup():
                self._storage.clear()

            return cleanup

        # the registration appends to a process-global list, pinning self (and, through the
        # kernel store, the per-kernel values) forever. Fine for module-level singletons -
        # the module pins them anyway - but per-component-instance singletons (use_task)
        # must call this cleanup on unmount or every mount leaks until process exit.
        # Instances created INSIDE a kernel additionally unregister at kernel close
        # (unmount cleanups don't run when the whole kernel goes away).
        self._on_kernel_start_cleanup = _on_kernel_start_scoped_to_creator(reset)

    def __set__(self, obj, value):
        raise AttributeError("Can't set a singleton")


class Computed(Reactive[S]):
    _storage: KernelStore[S]

    def __init__(self, f: Callable[[], S], key=None):
        if reacton.core.get_render_context(required=False) is not None:
            site = _app_call_site()
            if site is not None:
                _warn_once(
                    site,
                    f"A Computed was created during a render ({site}). This creates a new Computed — and new "
                    "registrations and subscriptions — on every render. Create it at module level, or use "
                    "use_memo for values derived inside a component.",
                )
        self.f = f

        def on_change(*ignore):
            with self._auto_subscriber.value:
                self.set(f())

        import functools

        self._auto_subscriber = Singleton(functools.wraps(AutoSubscribeContextManager)(lambda: AutoSubscribeContextManager(on_change)))

        @functools.wraps(f)
        def factory():
            v = self._auto_subscriber.value
            with v:
                return f()

        super().__init__(KernelStoreFactory(factory, key=key))

        # reset on kernel restart (e.g. hot reload). Keep the cleanup (a discarded
        # one can never be called: a Computed created inside a component pinned
        # itself, its closures and their captures in the process-global list forever)
        # and unregister at kernel close for kernel-created instances.
        def reset():
            def cleanup():
                self._storage.clear()

            return cleanup

        self._on_kernel_start_cleanup = _on_kernel_start_scoped_to_creator(reset)

    def __repr__(self):
        value = super().__repr__()
        return "<Computed" + value[len("<Reactive") : -1]


@overload
def computed(
    f: None,
    *,
    key: Optional[str] = ...,
) -> Callable[[Callable[[], T]], Reactive[T]]: ...


@overload
def computed(
    f: Callable[[], T],
    *,
    key: Optional[str] = ...,
) -> Reactive[T]: ...


def computed(
    f: Union[None, Callable[[], T]],
    *,
    key: Optional[str] = None,
) -> Union[Callable[[Callable[[], T]], Reactive[T]], Reactive[T]]:
    """Creates a reactive variable that is set to the return value of the function.

    The value will be updated when any of the reactive variables used in the function
    change.

    ## Example

    ```solara
    import solara
    import solara.lab


    a = solara.reactive(1)
    b = solara.reactive(2)

    @solara.lab.computed
    def total():
        return a.value + b.value

    def reset():
        a.value = 1
        b.value = 2

    @solara.component
    def Page():
        print(a, b, total)
        solara.IntSlider("a", value=a)
        solara.IntSlider("b", value=b)
        solara.Text(f"a + b = {total.value}")
        solara.Button("reset", on_click=reset)
    ```

    """

    def wrapper(f: Callable[[], T]):
        return Computed(f, key=key)

    if f is None:
        return wrapper
    else:
        return wrapper(f)


class ReactiveField(Reactive[T]):
    def __init__(self, field: "FieldBase", equals: Callable[[Any, Any], bool] = equals_extra):
        # super().__init__()  # type: ignore
        # We skip the Reactive constructor, because we do not need it, but we do
        # want to be an instanceof for use in use_reactive
        ValueBase.__init__(self, equals=equals)
        self._field = field
        field = field
        while not isinstance(field, ValueBase):
            field = field._parent
        self._root = field
        assert isinstance(self._root, ValueBase)

    def __str__(self):
        return str(self._field)

    def __repr__(self):
        return f"<Reactive field {self._field}>"

    @property
    def lock(self):
        return self._root.lock

    def subscribe(self, listener: Callable[[T], None], scope: Optional[ContextManager] = None):
        def on_change(new, old):
            try:
                new_value = self._field.get(new)
            except IndexError:
                return  # the current design choice to silently drop the update message
            except KeyError:
                return  # same
            old_value = self._field.get(old)
            if not self.equals(new_value, old_value):
                listener(new_value)

        return self._root.subscribe_change(on_change, scope=scope)

    def subscribe_change(self, listener: Callable[[T, T], None], scope: Optional[ContextManager] = None):
        def on_change(new, old):
            try:
                new_value = self._field.get(new)
            except IndexError:
                return  # see subscribe
            except KeyError:
                return  # see subscribe
            old_value = self._field.get(old)
            if not self.equals(new_value, old_value):
                listener(new_value, old_value)

        return self._root.subscribe_change(on_change, scope=scope)

    def get(self, add_watch=None) -> T:
        if add_watch is not None:
            warnings.warn("add_watch is deprecated, use .peek()", DeprecationWarning)
        if thread_local.reactive_used is not None:
            thread_local.reactive_used.add(self)
        if thread_local.reactive_watch is not None:
            thread_local.reactive_watch(self)
        # peek to avoid parents also adding themselves to the reactive_used set
        return self._field.peek()

    def peek(self) -> T:
        return self._field.peek()

    def set(self, value: T):
        self._field.set(value)

    def update(self, *args, **kwargs):
        ValueBase.update(cast(ValueBase, self), *args, **kwargs)


def Ref(field: T) -> Reactive[T]:
    _field = cast(FieldBase, field)
    return cast(Reactive[T], ReactiveField[T](_field))


class FieldBase:
    _parent: Any

    def __getattr__(self, key):
        if key in ["_parent", "set", "_lock"] or key.startswith("__"):
            return self.__dict__[key]
        return FieldAttr(self, key)

    def __getitem__(self, key):
        return FieldItem(self, key)

    def get(self, obj=None):
        raise NotImplementedError

    def set(self, value):
        raise NotImplementedError


class Fields(FieldBase):
    def __init__(self, state: ValueBase):
        self._parent = state
        self._lock = state.lock

    def get(self, obj=None):
        # we are at the root, so override the object
        # so we can get the 'old' value
        if obj is not None:
            return obj
        return self._parent.get()

    def peek(self, obj=None):
        # we are at the root, so override the object
        # so we can get the 'old' value
        if obj is not None:
            return obj
        return self._parent.peek()

    def set(self, value):
        self._parent.set(value)

    def __repr__(self):
        return repr(self._parent)


class FieldAttr(FieldBase):
    def __init__(self, parent, key: str):
        self._parent = parent
        self.key = key
        self._lock = parent._lock

    def get(self, obj=None):
        obj = self._parent.get(obj)
        return getattr(obj, self.key)

    def peek(self, obj=None):
        obj = self._parent.peek(obj)
        return getattr(obj, self.key)

    def set(self, value):
        with self._lock:
            parent_value = self._parent.peek()
            if isinstance(self.key, str):
                parent_value = merge_state(parent_value, **{self.key: value})
                self._parent.set(parent_value)
            else:
                raise TypeError(f"Type of key {self.key!r} is not supported")

    def __str__(self):
        return f".{self.key}"

    def __repr__(self):
        return f"<Field {self._parent}{self}>"


class FieldItem(FieldBase):
    def __init__(self, parent, key: str):
        self._parent = parent
        self.key = key
        self._lock = parent._lock

    def get(self, obj=None):
        obj = self._parent.get(obj)
        return getitem(obj, self.key)

    def peek(self, obj=None):
        obj = self._parent.peek(obj)
        return getitem(obj, self.key)

    def set(self, value):
        with self._lock:
            parent_value = self._parent.peek()
            if isinstance(self.key, int) and isinstance(parent_value, (list, tuple)):
                parent_type = type(parent_value)
                parent_value = parent_value.copy()  # type: ignore
                parent_value[self.key] = value
                self._parent.set(parent_type(parent_value))
            else:
                parent_value = merge_state(parent_value, **{self.key: value})
                self._parent.set(parent_value)


class AutoSubscribeContextManagerBase:
    # a render loop might trigger a new render loop of a differtent render context
    # so we want to save, and restore the current reactive_used
    reactive_used: Optional[Set[ValueBase]] = None
    on_change: Callable[[], None]

    def __init__(self):
        # Committed subscriptions of the last completed compute: reactive -> unsubscribe.
        # Replaced atomically at commit, never mutated in place: an instance is shared by
        # every thread that recomputes (render threads, task threads), and in-place
        # mutation orphaned unsubscribe closures when computes ran concurrently
        # (docs/memory-usage-inspection.md, case study 4 epilogue).
        self._committed: Dict[ValueBase, Callable] = {}
        # in-flight compute state lives per thread, never on the instance
        self._run_local = threading.local()
        # held only for the commit swap-and-diff and unsubscribe_all: microseconds, no
        # user code inside, acquires no other locks — cannot join a lock-order cycle
        self._commit_lock = threading.Lock()
        self.on_change = lambda: None
        # set by unsubscribe_all: once the owner is done (component unmounted or
        # kernel closed), add() must refuse to resubscribe — a recompute racing the
        # cleanup (task threads, listener fires during teardown) would otherwise
        # re-create the subscriptions on a dead scope, undoing the cleanup
        self.closed = False

    @property
    def subscribed(self) -> Dict[ValueBase, Callable]:
        # introspection view (tests, debugging): the last committed subscriptions
        return self._committed

    @property
    def subscribed_previous_run(self) -> Dict[ValueBase, Callable]:
        return self._committed

    def unsubscribe_all(self):
        """Unsubscribe everything: the owner's end-of-life cleanup (unmount or kernel close)."""
        # flip the flag FIRST: a concurrent add() checks it before and after writing,
        # and a concurrent commit re-checks it under the lock
        self.closed = True
        with self._commit_lock:
            old = self._committed
            self._committed = {}
        for unsubscribe in old.values():
            unsubscribe()

    def add(self, reactive: ValueBase):
        if self.closed:
            return
        run: Optional[Dict[ValueBase, Callable]] = getattr(self._run_local, "run", None)
        snapshot: Dict[ValueBase, Callable] = getattr(self._run_local, "snapshot", None) or {}
        if run is None:
            # not inside our compute span (defensive; reactive_watch only points here
            # between __enter__ and __exit__)
            return
        relevant_reactive = reactive
        if isinstance(reactive, ValueSubField):
            root = reactive._root
            if root in run or root in snapshot:
                # we already subscribed to this reactive's root
                return
            else:
                # we are subscribing to this reactive's root
                pass

        # TODO: we could see if we are the root of any of the subscribed fields,
        # and remove that field.
        if relevant_reactive not in run:
            if relevant_reactive in snapshot:
                # reuse the existing subscription; the commit diff keeps it alive
                run[relevant_reactive] = snapshot[relevant_reactive]
            else:
                with _managed_subscription():
                    unsubscribe = relevant_reactive.subscribe_change(lambda *args: self.on_change())
                run[relevant_reactive] = unsubscribe
                if self.closed:
                    # raced with unsubscribe_all: it cannot see our run dict — undo
                    # our own write (unsubscribe is idempotent via discard semantics)
                    unsubscribe()
                    run.pop(relevant_reactive, None)

    def __enter__(self):
        self._run_local.run = {}
        self._run_local.snapshot = self._committed  # atomic reference read
        self._run_local.reactive_used_before = thread_local.reactive_used
        self._run_local.previous_reactive_watch = thread_local.reactive_watch
        thread_local.reactive_watch = self.add
        self.reactive_used = thread_local.reactive_used = set()

    def __exit__(self, exc_type, exc_val, exc_tb):
        thread_local.reactive_used = self._run_local.reactive_used_before
        thread_local.reactive_watch = self._run_local.previous_reactive_watch
        # drop saved references (a Computed's manager must not retain the component
        # manager's bound method: it keeps the _RenderContext alive through cells)
        self._run_local.reactive_used_before = None
        self._run_local.previous_reactive_watch = None
        run = self._run_local.run
        snapshot: Dict[ValueBase, Callable] = self._run_local.snapshot or {}
        self._run_local.run = None
        self._run_local.snapshot = None
        if run is None:
            return
        # commit invariant: _committed only ever holds LIVE closures, so old.get(r) read
        # under the lock is a liveness oracle. Entries add() copied verbatim from the
        # enter-time snapshot are "reused": their closure was live at __enter__, but a
        # concurrent commit may have dropped and unsubscribed it since (the enter snapshot
        # is stale vs the exit-time committed dict). Identity recovers the reused set with
        # no bookkeeping in add(): every other entry is a closure we subscribed this run.
        reused = {r for r, unsubscribe in run.items() if snapshot.get(r) is unsubscribe}
        # For each reused dep, adopt whatever closure is currently live (pure dict work,
        # under the lock); a dep with no live closure was genuinely orphaned by a
        # concurrent drop and must be re-subscribed (user code, OUTSIDE the lock), after
        # which we re-validate under the lock. Bounded: each pass either commits or
        # converts >=1 reused dep to an owned fresh subscription (reused only shrinks).
        old: Dict[ValueBase, Callable] = {}
        while True:
            need_subscribe = []
            with self._commit_lock:
                old = self._committed
                closed = self.closed
                if not closed:
                    for reactive in reused:
                        live = old.get(reactive)
                        if live is not None:
                            run[reactive] = live  # adopt the currently-live closure
                        else:
                            need_subscribe.append(reactive)  # orphaned: no live listener
                    if not need_subscribe:
                        self._committed = run
            if closed or not need_subscribe:
                break
            for reactive in need_subscribe:
                with _managed_subscription():
                    run[reactive] = reactive.subscribe_change(lambda *args: self.on_change())
                reused.discard(reactive)  # now a closure we own; never re-validated again
        # diff outside the lock: unsubscribe whatever the new committed state no longer
        # holds (adopted closures are `is` their old entry, so they survive the diff).
        for reactive, unsubscribe in old.items():
            if closed or run.get(reactive) is not unsubscribe:
                unsubscribe()
        if closed:
            # closed while computing: our run must not survive either
            for reactive, unsubscribe in run.items():
                if old.get(reactive) is not unsubscribe:
                    unsubscribe()


class Context:
    def __init__(self, render_context, kernel_context):
        # combine the render context *and* the kernel context into one context
        # Use weakrefs for both render_context and kernel_context to avoid
        # preventing garbage collection when contexts are closed.
        # Subscriptions (e.g. from Computed/AutoSubscribeContextManager)
        # capture Context objects in listeners dicts. Without weakrefs, these
        # keep the contexts alive even after close(), causing memory leaks.
        if render_context is not None:
            self._render_context_ref: Optional[weakref.ref] = weakref.ref(render_context)
            self._render_context_id: Optional[int] = id(render_context)
        else:
            self._render_context_ref = None
            self._render_context_id = None
        # Use weakref for kernel_context when possible. nullcontext (used when
        # there is no kernel) doesn't support weakrefs, so fall back to strong ref.
        try:
            self._kernel_context_ref: Optional[weakref.ref] = weakref.ref(kernel_context)
            self._kernel_context_id: Optional[int] = id(kernel_context)
            self._kernel_context_strong: Any = None
        except TypeError:
            self._kernel_context_ref = None
            self._kernel_context_id = id(kernel_context) if kernel_context is not None else None
            self._kernel_context_strong = kernel_context

    @property
    def render_context(self):
        if self._render_context_ref is not None:
            return self._render_context_ref()
        return None

    @property
    def kernel_context(self):
        if self._kernel_context_ref is not None:
            return self._kernel_context_ref()
        return self._kernel_context_strong

    def __enter__(self):
        rc = self.render_context
        if rc is not None:
            rc.__enter__()
        kc = self.kernel_context
        if kc is not None:
            kc.__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        rc = self.render_context
        if rc is not None:
            # this will trigger a render
            res1 = rc.__exit__(exc_type, exc_val, exc_tb)
        else:
            res1 = None

        # pop the current context from the stack
        kc = self.kernel_context
        if kc is not None:
            res2 = kc.__exit__(exc_type, exc_val, exc_tb)
        else:
            res2 = None
        return res1 or res2

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, Context):
            return False
        return self._render_context_id == value._render_context_id and self._kernel_context_id == value._kernel_context_id

    def __hash__(self) -> int:
        return hash(self._render_context_id) ^ hash(self._kernel_context_id)

    def __repr__(self) -> str:
        return f"Context(render_context={self.render_context}, kernel_context={self.kernel_context})"


class AutoSubscribeContextManagerReacton(AutoSubscribeContextManagerBase):
    def __init__(self, element: solara.Element):
        self.element = element
        super().__init__()

    def __enter__(self):
        _, set_counter = solara.use_state(0, key="auto_subscribe_force_update_counter")

        def force_update():
            # can we do just x+1 to collapse multiple updates into one?
            if logger.isEnabledFor(logging.INFO):
                frame = _find_outside_solara_frame()
                if frame is not None:
                    tb = inspect.getframeinfo(frame)
                else:
                    tb = None
                if tb is not None and tb.code_context:
                    code = tb.code_context[0]
                    hint = f"\n{tb.filename}:{tb.lineno}\n{code.rstrip()}"
                else:
                    hint = "<No code context available>"
                logger.info("A rerender was triggered by: %s", hint)

            set_counter(lambda x: x + 1)

        super().__enter__()
        self.on_change = force_update

        def on_close():
            def cleanup():
                self.unsubscribe_all()

            return cleanup

        solara.use_effect(on_close, [])


class AutoSubscribeContextManager(AutoSubscribeContextManagerBase):
    def __init__(self, on_change: Callable[[], None]):
        super().__init__()
        self.on_change = on_change
        # This instance owns its subscriptions, and (for Computed) is created once
        # per kernel: unsubscribe when that kernel closes, or every kernel leaves
        # its subscriptions — pinning the on_change closure and everything it
        # captures — behind on process-lifetime stores, forever
        # (docs/memory-usage-inspection.md, case study 4).
        if _using_solara_server():
            import solara.server.kernel_context

            if solara.server.kernel_context.has_current_context():
                solara.server.kernel_context.get_current_context().on_close(self.unsubscribe_all)


# alias for compatibility
State = Reactive
ValueSubField = ReactiveField

auto_subscribe_context_manager = AutoSubscribeContextManagerReacton
reacton.core._component_context_manager_classes.append(auto_subscribe_context_manager)
