import dataclasses
import sys
import threading
from operator import getitem
from typing import Any, Callable, Dict, Generic, Set, Tuple, TypeVar, Union, cast

import react_ipywidgets as react

from solara import _using_solara_server

T = TypeVar("T")
TS = TypeVar("TS")
S = TypeVar("S")  # used for state

local = threading.local()
_DEBUG = False


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
        if new_state != prev_state.current:
            prev_state.current = new_state
            force_update()

    react.use_effect(lambda: subscribe(on_store_change), [])
    return state


def use_sync_external_store_with_selector(subscribe, get_snapshot: Callable[[], Any], selector):
    return use_sync_external_store(subscribe, lambda: selector(get_snapshot()))


def merge_state(d1: S, **kwargs) -> S:
    if dataclasses.is_dataclass(d1):
        return dataclasses.replace(d1, **kwargs)
    if "pydantic" in sys.modules and isinstance(d1, sys.modules["pydantic"].BaseModel):
        return type(d1)(**{**d1.dict(), **kwargs})  # type: ignore
    return cast(S, {**cast(dict, d1), **kwargs})


class ValueBase(Generic[T]):
    def __init__(self, merge: Callable = merge_state):
        self.merge = merge
        self.listeners: Set[Callable[[T], None]] = set()
        self.listeners2: Set[Callable[[T, T], None]] = set()

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

    def get(self) -> T:
        raise NotImplementedError

    def subscribe(self, listener: Callable[[T], None]):
        self.listeners.add(listener)

        def cleanup():
            self.listeners.remove(listener)

        return cleanup

    def subscribe_change(self, listener: Callable[[T, T], None]):
        self.listeners2.add(listener)

        def cleanup():
            self.listeners2.remove(listener)

        return cleanup

    def update(self, _f=None, **kwargs):
        if _f is not None:
            assert not kwargs
            with self.lock:
                kwargs = _f(self.get())
        with self.lock:
            # important to have this part thread-safe
            new = self.merge(self.get(), **kwargs)
            self.set(new)

    def fire(self, new: T, old: T):
        for listener in self.listeners.copy():
            listener(new)
        for listener2 in self.listeners2.copy():
            listener2(new, old)

    def use_value(self) -> T:
        # .use with the default argument doesn't give good type inference
        return self.use()

    def use(self, selector: Callable[[T], TS] = lambda x: x) -> TS:  # type: ignore
        slice = use_sync_external_store_with_selector(
            self.subscribe,
            self.get,
            selector,
        )
        return slice

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


class ConnectionStore(ValueBase[S]):
    _global_dict: Dict[str, S] = {}  # outside of solara context, this is used
    scope_lock = threading.Lock()

    def __init__(self, default_value: S = None, key=None):
        super().__init__()
        self.default_value = default_value
        cls = type(default_value)
        self.storage_key = key or (cls.__module__ + ":" + cls.__name__ + "-" + str(id(default_value)))
        self._global_dict = {}
        # since a set can trigger events, which can trigger new updates, we need a recursive lock
        self._lock = threading.RLock()

    @property
    def lock(self):
        return self._lock

    def _get_dict(self):
        scope_dict = self._global_dict
        if _using_solara_server():
            import solara.server.app

            try:
                context = solara.server.app.get_current_context()
            except:  # noqa
                pass  # do we need to be more strict?
            else:
                scope_dict = cast(Dict[str, S], context.user_dicts)
        return scope_dict

    def get(self):
        scope_dict = self._get_dict()
        if self.storage_key not in scope_dict:
            with self.scope_lock:
                if self.storage_key not in scope_dict:
                    # we assume immutable, so don't make a copy
                    scope_dict[self.storage_key] = self.default_value
        return scope_dict[self.storage_key]

    def set(self, value: S):
        scope_dict = self._get_dict()
        old = self.get()
        scope_dict[self.storage_key] = value

        if _DEBUG:
            import traceback

            traceback.print_stack(limit=17, file=sys.stdout)

            print("change old", old)  # noqa
            print("change new", old)  # noqa

        self.fire(value, old)


class Reactive(ValueBase[S]):
    _storage: ValueBase[S]

    def __init__(self, default_value: Union[S, ValueBase[S]]):
        super().__init__()
        if not isinstance(default_value, ValueBase):
            self._storage = ConnectionStore(default_value, key=id(self))
        else:
            self._storage = default_value
        self.__post__init__()

    @property
    def lock(self):
        return self._storage.lock

    def __post__init__(self):
        pass

    def update(self, **kwargs):
        self._storage.update(**kwargs)

    def set(self, value: S):
        self._storage.set(value)

    def get(self) -> S:
        return self._storage.get()

    def subscribe(self, listener: Callable[[S], None]):
        return self._storage.subscribe(listener)

    def subscribe_change(self, listener: Callable[[S, S], None]):
        return self._storage.subscribe_change(listener)

    def computed(self, f: Callable[[S], T]) -> "Computed[T]":
        return Computed(f, self)


class Computed(Generic[T]):
    def __init__(self, compute: Callable[[S], T], state: Reactive[S]):
        self.compute = compute
        self.state = state

    def get(self) -> T:
        return self.compute(self.state.get())

    def subscribe(self, listener: Callable[[T], None]):
        return self.state.subscribe(lambda _: listener(self.get()))

    def use(self, selector: Callable[[T], T]) -> T:
        slice = use_sync_external_store_with_selector(
            self.subscribe,
            self.get,
            selector,
        )
        return slice


class ValueSubField(ValueBase[T]):
    def __init__(self, field: "FieldBase"):
        super().__init__()  # type: ignore
        self._field = field
        field = field
        while not isinstance(field, ValueBase):
            field = field._parent
        self._root = field
        assert isinstance(self._root, ValueBase)

    @property
    def lock(self):
        return self._root.lock

    def subscribe(self, listener: Callable[[T], None]):
        def on_change(new, old):
            new_value = self._field.get(new)
            old_value = self._field.get(old)
            if new_value != old_value:
                listener(new_value)

        return self._root.subscribe_change(on_change)

    def get(self, obj=None) -> T:
        return self._field.get(obj)

    def set(self, value: T):
        self._field.set(value)


def Ref(field: T) -> ValueSubField[T]:
    _field = cast(FieldBase, field)
    return ValueSubField[T](_field)


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

    def set(self, value):
        self._parent.set(value)


class FieldAttr(FieldBase):
    def __init__(self, parent, key: str):
        self._parent = parent
        self.key = key
        self._lock = parent._lock

    def get(self, obj=None):
        obj = self._parent.get(obj)
        return getattr(obj, self.key)

    def set(self, value):
        with self._lock:
            parent_value = self._parent.get()
            if isinstance(self.key, str):
                parent_value = merge_state(parent_value, **{self.key: value})
                self._parent.set(parent_value)
            else:
                raise TypeError(f"Type of key {self.key!r} is not supported")


class FieldItem(FieldBase):
    def __init__(self, parent, key: str):
        self._parent = parent
        self.key = key
        self._lock = parent._lock

    def get(self, obj=None):
        obj = self._parent.get(obj)
        return getitem(obj, self.key)

    def set(self, value):
        with self._lock:
            parent_value = self._parent.get()
            if isinstance(self.key, int) and isinstance(parent_value, (list, tuple)):
                parent_type = type(parent_value)
                parent_value = parent_value.copy()  # type: ignore
                parent_value[self.key] = value
                self._parent.set(parent_type(parent_value))
            else:
                parent_value = merge_state(parent_value, **{self.key: value})
                self._parent.set(parent_value)


# alias for compatibility
State = Reactive
