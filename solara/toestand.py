import contextlib
import dataclasses
import logging
import sys
import threading
import warnings
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
from reacton.utils import equals

import solara
from solara import _using_solara_server
from solara.server import settings

T = TypeVar("T")
TS = TypeVar("TS")
S = TypeVar("S")  # used for state
logger = logging.getLogger("solara.toestand")
solara_logger = logging.getLogger("solara")

_DEBUG = False


class ThreadLocal(threading.local):
    reactive_used: Optional[Set["ValueBase"]] = None


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
        if not equals(new_state, prev_state.current):
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
        return type(d1)(**{**d1.dict(), **kwargs})  # type: ignore
    return cast(S, {**cast(dict, d1), **kwargs})


class ValueBase(Generic[T]):
    def __init__(self, merge: Callable = merge_state):
        self.merge = merge
        self.listeners: Dict[str, Set[Tuple[Callable[[T], None], Optional[ContextManager]]]] = defaultdict(set)
        self.listeners2: Dict[str, Set[Tuple[Callable[[T, T], None], Optional[ContextManager]]]] = defaultdict(set)
        if settings.main.log_level in ["DEBUG", "INFO"]:
            import inspect

            for frame in inspect.stack():
                file = frame.filename
                if (
                    not (
                        file.endswith("solara/toestand.py")
                        or file.endswith("solara/reactive.py")
                        or file.endswith("solara/hooks/use_reactive.py")
                        or file.endswith("reacton/core.py")
                        or file.endswith("components/markdown.py")
                    )
                    and frame.code_context is not None
                ):
                    if "=" not in frame.code_context[0]:
                        continue
                    elif any(op in frame.code_context[0].split("=")[1].lower() for op in ["reactive", "use_memo", "computed", "singleton"]):
                        declaration = frame.code_context[0].split("=")[0].strip()
                        if ":" in declaration:
                            declaration = declaration.split(":")[0].strip()
                        self._varname: Optional[str] = declaration
                        logger.info("found varname: " + declaration)
                        break
                # Markdown case is special, because the stacktrace ends at
                # https://github.com/widgetti/solara/blob/604d2e54146308d64a209334d0314d2baba75108/solara/components/markdown.py#L368
                elif file.endswith("components/markdown.py"):
                    self._varname = "markdown_content"
                    break
            if not hasattr(self, "_varname"):
                logger.info("No varname found")
                self._varname = None

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
        scope_id = self._get_scope_key()
        self.listeners[scope_id].add((listener, scope))

        def cleanup():
            self.listeners[scope_id].remove((listener, scope))

        return cleanup

    def subscribe_change(self, listener: Callable[[T, T], None], scope: Optional[ContextManager] = None):
        scope_id = self._get_scope_key()
        self.listeners2[scope_id].add((listener, scope))

        def cleanup():
            self.listeners2[scope_id].remove((listener, scope))

        return cleanup

    def fire(self, new: T, old: T):
        if settings.main.log_level in ["DEBUG", "INFO"] and self._varname is not None:
            logger.info(f"value of {self._varname if self._varname is not None else ''} changed from %s to %s, will fire events", old, new)
        else:
            logger.info("value changed from %s to %s, will fire events", old, new)
        scope_id = self._get_scope_key()
        scopes = set()
        for listener, scope in self.listeners[scope_id].copy():
            if scope is not None:
                scopes.add(scope)
        for listener2, scope in self.listeners2[scope_id].copy():
            if scope is not None:
                scopes.add(scope)
        stack = contextlib.ExitStack()
        with contextlib.ExitStack() as stack:
            for scope in scopes:
                stack.enter_context(scope)
            for listener, scope in self.listeners[scope_id].copy():
                listener(new)
            for listener2, scope in self.listeners2[scope_id].copy():
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


# the default store for now, stores in a global dict, or when in a solara
# context, in the solara user context


class KernelStore(ValueBase[S], ABC):
    _global_dict: Dict[str, S] = {}  # outside of solara context, this is used
    # we keep a counter per type, so the storage keys we generate are deterministic
    _type_counter: Dict[Any, int] = defaultdict(int)
    scope_lock = threading.RLock()

    def __init__(self, key=None):
        super().__init__()
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
        if equals(old, value):
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


class KernelStoreValue(KernelStore[S]):
    default_value: S

    def __init__(self, default_value: S, key=None):
        self.default_value = default_value
        cls = type(default_value)
        if key is None:
            with KernelStoreValue.scope_lock:
                index = self._type_counter[cls]
                self._type_counter[cls] += 1
            key = cls.__module__ + ":" + cls.__name__ + ":" + str(index)
        super().__init__(key=key)

    def initial_value(self) -> S:
        return self.default_value


class KernelStoreFactory(KernelStore[S]):
    def __init__(self, factory: Callable[[], S], key=None):
        self.factory = factory
        try:
            prefix = factory.__qualname__
        except Exception:
            prefix = repr(factory)
        if key is None:
            with KernelStore.scope_lock:
                index = self._type_counter[prefix]
                self._type_counter[prefix] += 1
            try:
                key = factory.__module__ + ":" + prefix + ":" + str(index)
            except Exception:
                key = prefix + ":" + str(index)
        super().__init__(key=key)

    def initial_value(self) -> S:
        return self.factory()


class Reactive(ValueBase[S]):
    _storage: ValueBase[S]

    def __init__(self, default_value: Union[S, ValueBase[S]], key=None):
        super().__init__()
        if not isinstance(default_value, ValueBase):
            self._storage = KernelStoreValue(default_value, key=key)
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
        import solara.server.kernel_context

        super().__init__(KernelStoreFactory(factory, key=key))

        # reset on kernel restart (e.g. hot reload)
        def reset():
            def cleanup():
                self._storage.clear()

            return cleanup

        solara.server.kernel_context.on_kernel_start(reset)

    def __set__(self, obj, value):
        raise AttributeError("Can't set a singleton")


class Computed(Reactive[S]):
    _storage: KernelStore[S]

    def __init__(self, f: Callable[[], S], key=None):
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

        solara.server.kernel_context.on_kernel_start(reset)

    def __repr__(self):
        value = super().__repr__()
        return "<Computed" + value[len("<Reactive") : -1]


@overload
def computed(
    f: None,
    *,
    key: Optional[str] = ...,
) -> Callable[[Callable[[], T]], Reactive[T]]:
    ...


@overload
def computed(
    f: Callable[[], T],
    *,
    key: Optional[str] = ...,
) -> Reactive[T]:
    ...


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
    def __init__(self, field: "FieldBase"):
        # super().__init__()  # type: ignore
        # We skip the Reactive constructor, because we do not need it, but we do
        # want to be an instanceof for use in use_reactive
        ValueBase.__init__(self)
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
            if not equals(new_value, old_value):
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
            if not equals(new_value, old_value):
                listener(new_value, old_value)

        return self._root.subscribe_change(on_change, scope=scope)

    def get(self, add_watch=None) -> T:
        if add_watch is not None:
            warnings.warn("add_watch is deprecated, use .peek()", DeprecationWarning)
        if thread_local.reactive_used is not None:
            thread_local.reactive_used.add(self)
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
    reactive_added_previous_run: Optional[Set[ValueBase]] = None
    subscribed: Dict[ValueBase, Callable]

    def __init__(self):
        self.subscribed = {}

    def update_subscribers(self, change_handler, scope=None):
        assert self.reactive_used is not None
        reactive_used = self.reactive_used
        # remove subfields for which we already listen to it's root reactive value
        reactive_used_subfields = {k for k in reactive_used if isinstance(k, ValueSubField)}
        reactive_used = reactive_used - reactive_used_subfields
        # only add subfield for which we don't listen to it's parent
        for reactive_used_subfield in reactive_used_subfields:
            if reactive_used_subfield._root not in reactive_used:
                reactive_used.add(reactive_used_subfield)
        added = reactive_used - (self.reactive_added_previous_run or set())

        removed = (self.reactive_added_previous_run or set()) - reactive_used

        for reactive in added:
            if reactive not in self.subscribed:
                unsubscribe = reactive.subscribe_change(change_handler, scope=scope)
                self.subscribed[reactive] = unsubscribe
        for reactive in removed:
            unsubscribe = self.subscribed[reactive]
            unsubscribe()
            del self.subscribed[reactive]
        self.reactive_added_previous_run = added

    def unsubscribe_all(self):
        for reactive in self.subscribed:
            unsubscribe = self.subscribed[reactive]
            unsubscribe()

    def __enter__(self):
        self.reactive_used_before = thread_local.reactive_used
        self.reactive_used = thread_local.reactive_used = set()
        assert thread_local.reactive_used is self.reactive_used, f"{hex(id(thread_local.reactive_used))} vs {hex(id(self.reactive_used))}"

    def __exit__(self, exc_type, exc_val, exc_tb):
        thread_local.reactive_used = self.reactive_used_before


class AutoSubscribeContextManagerReacton(AutoSubscribeContextManagerBase):
    def __init__(self, element: solara.Element):
        self.element = element
        super().__init__()

    def __enter__(self):
        _, set_counter = solara.use_state(0, key="auto_subscribe_force_update_counter")

        def force_update(new_value, old_value):
            # can we do just x+1 to collapse multiple updates into one?
            set_counter(lambda x: x + 1)

        super().__enter__()

        def update_subscribers():
            self.update_subscribers(force_update, scope=reacton.core.get_render_context(required=True))

        solara.use_effect(update_subscribers, None)

        def on_close():
            def cleanup():
                assert self.reactive_added_previous_run is not None
                self.unsubscribe_all()

            return cleanup

        solara.use_effect(on_close, [])


class AutoSubscribeContextManager(AutoSubscribeContextManagerBase):
    on_change: Callable[[], None]

    def __init__(self, on_change: Callable[[], None]):
        super().__init__()
        self.on_change = on_change

    def __enter__(self):
        super().__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        value = super().__exit__(exc_type, exc_val, exc_tb)
        self.update_subscribers(self.on_change)
        return value


# alias for compatibility
State = Reactive
ValueSubField = ReactiveField

auto_subscribe_context_manager = AutoSubscribeContextManagerReacton
reacton.core._component_context_manager_classes.append(auto_subscribe_context_manager)
