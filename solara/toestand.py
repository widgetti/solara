import dataclasses
import inspect
import logging
import os
import sys
import threading
from types import FrameType
import warnings
import copy
from abc import ABC, abstractmethod
from collections import defaultdict
from operator import getitem
from typing import (
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

T = TypeVar("T")
TS = TypeVar("TS")
S = TypeVar("S")  # used for state
logger = logging.getLogger("solara.toestand")

_DEBUG = False


class ThreadLocal(threading.local):
    reactive_used: Optional[Set["ValueBase"]] = None
    reactive_watch: Optional[Callable[["ValueBase"], None]] = None


thread_local = ThreadLocal()


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

    react.use_effect(lambda: subscribe(on_store_change), [])
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

        def cleanup():
            self.listeners[scope_id].remove((listener, context))

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

        def cleanup():
            self.listeners2[scope_id].remove((listener, context))

        return cleanup

    def fire(self, new: T, old: T):
        logger.info("value change from %s to %s, will fire events", old, new)
        scope_id = self._get_scope_key()
        contexts = set()
        for listener, context in self.listeners[scope_id].copy():
            contexts.add(context)
        for listener2, context in self.listeners2[scope_id].copy():
            contexts.add(context)
        if contexts:
            for context in contexts:
                with context or nullcontext():
                    for listener, context_listener in self.listeners[scope_id].copy():
                        if context == context_listener:
                            listener(new)
                    for listener2, context_listener in self.listeners2[scope_id].copy():
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
    scope_lock = threading.RLock()

    def __init__(self, key: str, equals: Callable[[Any, Any], bool] = equals_extra):
        super().__init__(equals=equals)
        self.storage_key = key
        self._global_dict = {}
        # since a set can trigger events, which can trigger new updates, we need a recursive lock
        self._lock = threading.RLock()
        self.local = threading.local()

    @property
    def lock(self):
        return self._lock

    def _get_scope_key(self):
        scope_dict, scope_id = self._get_dict()
        return scope_id

    def _get_dict(self):
        scope_dict = self._global_dict
        scope_id = "global"
        if _using_solara_server():
            import solara.server.kernel_context

            try:
                context = solara.server.kernel_context.get_current_context()
            except RuntimeError:  # noqa
                pass  # do we need to be more strict?
            else:
                scope_dict = cast(Dict[str, S], context.user_dicts)
                scope_id = context.id
        return cast(Dict[str, S], scope_dict), scope_id

    def peek(self):
        return self.get()

    def get(self):
        scope_dict, scope_id = self._get_dict()
        if self.storage_key not in scope_dict:
            with self.scope_lock:
                if self.storage_key not in scope_dict:
                    # we assume immutable, so don't make a copy
                    scope_dict[self.storage_key] = self.initial_value()
        return scope_dict[self.storage_key]

    def clear(self):
        scope_dict, scope_id = self._get_dict()
        if self.storage_key in scope_dict:
            del scope_dict[self.storage_key]

    def set(self, value: S):
        scope_dict, scope_id = self._get_dict()
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
            with KernelStoreValue.scope_lock:
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
    with KernelStore.scope_lock:
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

    def __init__(self, default_value: Union[S, ValueBase[S]], key=None, equals=None):
        super().__init__()
        if not isinstance(default_value, ValueBase):
            self._storage = _call_storage_factory(default_value, key=key, equals=equals)
        else:
            self._storage = default_value
        self.__post__init__()
        self._name = None
        self._owner = None

    def __set_name__(self, owner, name):
        self._name = name
        self._owner = owner

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


class Singleton(Reactive[S]):
    _storage: KernelStore[S]

    def __init__(self, factory: Callable[[], S], key=None):
        import solara.lifecycle

        super().__init__(KernelStoreFactory(factory, key=key))

        # reset on kernel restart (e.g. hot reload)
        def reset():
            def cleanup():
                self._storage.clear()

            return cleanup

        solara.lifecycle.on_kernel_start(reset)

    def __set__(self, obj, value):
        raise AttributeError("Can't set a singleton")


class Computed(Reactive[S]):
    _storage: KernelStore[S]

    def __init__(self, f: Callable[[], S], key=None):
        import solara.lifecycle

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

        # reset on kernel restart (e.g. hot reload)
        def reset():
            def cleanup():
                self._storage.clear()

            return cleanup

        solara.lifecycle.on_kernel_start(reset)

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
    subscribed: Dict[ValueBase, Callable]
    subscribed_previous_run: Dict[ValueBase, Callable]
    on_change: Callable[[], None]
    previous_reactive_watch: Optional[Callable[["ValueBase"], None]] = None

    def __init__(self):
        self.subscribed = {}
        self.subscribed_previous_run = {}
        self.on_change = lambda: None

    def unsubscribe_previous(self):
        removed = set(self.subscribed_previous_run or set()) - set(self.subscribed)
        if removed:
            for reactive in removed:
                unsubscribe = self.subscribed_previous_run[reactive]
                unsubscribe()
                del self.subscribed_previous_run[reactive]

    def add(self, reactive: ValueBase):
        relevant_reactive = reactive
        if isinstance(reactive, ValueSubField):
            root = reactive._root
            if root in self.subscribed or root in self.subscribed_previous_run:
                # we already subscribed to this reactive's root
                return
            else:
                # we are subscribing to this reactive's root
                pass

        # TODO: we could see if we are the root of any of the subscribed fields,
        # and remove that field.
        if relevant_reactive not in self.subscribed:
            if relevant_reactive not in self.subscribed_previous_run:
                unsubscribe = relevant_reactive.subscribe_change(lambda *args: self.on_change())
                self.subscribed[relevant_reactive] = unsubscribe
            else:
                self.subscribed[relevant_reactive] = self.subscribed_previous_run[relevant_reactive]

    def unsubscribe_all(self):
        for reactive in self.subscribed:
            unsubscribe = self.subscribed[reactive]
            unsubscribe()

    def __enter__(self):
        self.subscribed = {}
        self.reactive_used_before = thread_local.reactive_used
        self.previous_reactive_watch = thread_local.reactive_watch
        thread_local.reactive_watch = self.add
        self.reactive_used = thread_local.reactive_used = set()

    def __exit__(self, exc_type, exc_val, exc_tb):
        thread_local.reactive_used = self.reactive_used_before
        thread_local.reactive_watch = self.previous_reactive_watch
        self.unsubscribe_previous()
        self.subscribed_previous_run = self.subscribed.copy()


class Context:
    def __init__(self, render_context, kernel_context):
        # combine the render context *and* the kernel context into one context
        self.render_context = render_context
        self.kernel_context = kernel_context

    def __enter__(self):
        if self.render_context is not None:
            self.render_context.__enter__()
        self.kernel_context.__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.render_context is not None:
            # this will trigger a render
            res1 = self.render_context.__exit__(exc_type, exc_val, exc_tb)
        else:
            res1 = None

        # pop the current context from the stack
        res2 = self.kernel_context.__exit__(exc_type, exc_val, exc_tb)
        return res1 or res2

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, Context):
            return False
        return self.render_context == value.render_context and self.kernel_context == value.kernel_context

    def __hash__(self) -> int:
        return hash(id(self.render_context)) ^ hash(id(self.kernel_context))

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


# alias for compatibility
State = Reactive
ValueSubField = ReactiveField

auto_subscribe_context_manager = AutoSubscribeContextManagerReacton
reacton.core._component_context_manager_classes.append(auto_subscribe_context_manager)
