import dataclasses
import sys
import threading
import typing
from collections import defaultdict
from operator import getitem
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    List,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
    overload,
)

import react_ipywidgets as react
from reacton.utils import equals

from solara import _using_solara_server

T = TypeVar("T")
K = TypeVar("K")
TS = TypeVar("TS")
S = TypeVar("S")  # used for state

local = threading.local()
_DEBUG = False


# TODO: do we want to use this?
# @typing_extensions.dataclass_transform()
class ModelBase:
    def __init_subclass__(
        cls,
        *,
        init: bool = True,
        frozen: bool = True,
        eq: bool = True,
        order: bool = True,
    ):
        pass

    def __init__(self, **kwargs):
        cls = type(self)
        for k, v in kwargs.items():
            self.__dict__[k] = v
        for name, value in vars(cls).items():
            if isinstance(value, Field) and name not in self.__dict__:
                default = value.default
                if default == dataclasses.MISSING:
                    if value.default_factory == dataclasses.MISSING:
                        raise TypeError(f"no default value for {name}")
                    default = value.default_factory()
                # setattr(self, name, default)
                # do not trigger the __set__
                self.__dict__[name] = default

    def __eq__(self, rhs):
        if not type(self) == type(rhs):
            return False
        for name, value in vars(type(self)).items():
            if isinstance(value, Field):
                if getattr(self, name) != getattr(rhs, name):
                    return False
        return True

    def __repr__(self):
        reprs = []
        cls = type(self)
        for name, value in vars(cls).items():
            if isinstance(value, Field):
                value = getattr(self, name)
                reprs.append(f"{name}={value!r}")
        return f"{cls.__name__}({', '.join(reprs)})"


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
        return dataclasses.replace(d1, **kwargs)
    if "pydantic" in sys.modules and isinstance(d1, sys.modules["pydantic"].BaseModel):
        return type(d1)(**{**d1.dict(), **kwargs})  # type: ignore
    if isinstance(d1, dict):
        return cast(S, {**cast(dict, d1), **kwargs})
    cls = type(d1)
    obj = cls()
    for k, v in vars(d1).items():
        # setattr(obj, k, v)
        obj.__dict__[k] = v
    for k, v in kwargs.items():
        # setattr(obj, k, v)
        obj.__dict__[k] = v
    return obj


class ValueBase(Generic[T]):
    def __init__(self, merge: Callable = merge_state, **kwargs):
        self.merge = merge
        self.listeners: Dict[str, Set[Callable[[T], None]]] = defaultdict(set)
        self.listeners2: Dict[str, Set[Callable[[T, T], None]]] = defaultdict(set)

    @property
    def lock(self) -> threading.RLock:
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

    def _get_scope_key(self):
        raise NotImplementedError

    def subscribe(self, listener: Callable[[T], None]):
        scope_id = self._get_scope_key()
        self.listeners[scope_id].add(listener)

        def cleanup():
            self.listeners[scope_id].remove(listener)

        return cleanup

    def subscribe_change(self, listener: Callable[[T, T], None]):
        scope_id = self._get_scope_key()
        self.listeners2[scope_id].add(listener)

        def cleanup():
            self.listeners2[scope_id].remove(listener)

        return cleanup

    def fire(self, new: T, old: T):
        scope_id = self._get_scope_key()
        for listener in self.listeners[scope_id].copy():
            listener(new)
        for listener2 in self.listeners2[scope_id].copy():
            listener2(new, old)

    def update(self, _f=None, **kwargs):
        if _f is not None:
            assert not kwargs
            with self.lock:
                kwargs = _f(self.get())
        with self.lock:
            # important to have this part thread-safe
            # breakpoint()
            new = self.merge(self.get(), **kwargs)
            self.set(new)

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
    def fields(self) -> Type[T]:
        # we lie about the return type, but in combination with
        # setter we can make type safe setters (see docs/tests)
        return cast(Type[T], FieldRoot(self))

    def setter(self, field: TS) -> Callable[[TS], None]:
        _field = cast(FieldBase, field)

        def setter(new_value: TS):
            _field.set(new_value)

        return cast(Callable[[TS], None], setter)


# the default store for now, stores in a global dict, or when in a solara
# context, in the solara user context


class ConnectionStore(ValueBase[T]):
    _global_dict: Dict[str, T] = {}  # outside of solara context, this is used
    scope_lock = threading.Lock()

    def __init__(self, default_value: T = None, key=None):
        super().__init__()
        self.default_value = default_value
        self.listeners: Dict[str, Set[Callable[[T], None]]] = defaultdict(set)
        self.listeners2: Dict[str, Set[Callable[[T, T], None]]] = defaultdict(set)

        cls = type(default_value)
        self.storage_key = key or (cls.__module__ + ":" + cls.__name__ + "-" + str(id(default_value)))
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
            import solara.server.app

            try:
                context = solara.server.app.get_current_context()
            except:  # noqa
                pass  # do we need to be more strict?
            else:
                scope_dict = cast(Dict[str, T], context.user_dicts)
                scope_id = context.id
        return cast(Dict[str, T], scope_dict), scope_id

    def get(self):
        scope_dict, scope_id = self._get_dict()
        if self.storage_key not in scope_dict:
            with self.scope_lock:
                if self.storage_key not in scope_dict:
                    # we assume immutable, so don't make a copy
                    scope_dict[self.storage_key] = self.default_value
        return scope_dict[self.storage_key]

    def set(self, value: T):
        scope_dict, scope_id = self._get_dict()
        old = self.get()
        if equals(old, value):
            return
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

    def __repr__(self):
        reprs = []
        cls = type(self)
        for name, value in vars(cls).items():
            if isinstance(value, Field):
                value = getattr(self, name)
                reprs.append(f"{name}={value!r}")
        return f"{cls.__name__}({', '.join(reprs)})"

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


# although we inherit from ValueBase, we don't need to implement the whole interface,
# since only the interface is exposed to pylance/mypy, but 'Field*' implements it.


class Field(ValueBase[S]):
    def __init__(self, default=dataclasses.MISSING, default_factory=dataclasses.MISSING):
        self.default = default
        self.default_factory = default_factory
        ValueBase.__init__(self)

    def __set_name__(self, owner, name):
        self._name = name

    def set(self, value: S):
        raise NotImplementedError("You should never set a field directly. Use the `object.field.value = ...` syntax.")

    def get(self) -> S:
        raise NotImplementedError("Should never be called directly. Use the `object.field.value` syntax.")

    @overload
    def __get__(self, obj: None = None, cls: Any = ...) -> "Field[S]":
        ...

    @overload
    def __get__(self, obj: "Any", cls: Any = ...) -> S:
        ...

    def __get__(self, obj: Any = None, cls: Any = None) -> Union[S, "Field[S]"]:
        if obj is None:
            return self
        else:
            return obj.__dict__[self._name]

    def __set__(self, obj: Any, value: S):
        self.set(value)


class Bears(ModelBase, frozen=True):
    type: Field[str] = Field("brown")
    count: Field[int] = Field(1)


# bears = Bears()

# bears.type.capitalize()
# print(bears.type)

# # Bears.type.set("black")

# bears.fie

# class Bears(ModelBase, frozen=True):
#     type : Field[str] = Field("brown")
#     count : Field[int] = Field(1)

if typing.TYPE_CHECKING:

    class FieldList(ValueBase[List[S]]):
        def __getitem__(self, item) -> Type[S]:
            raise NotImplementedError()

else:

    class FieldList(Field[List[S]]):
        def __getitem__(self, item) -> Type[S]:
            raise NotImplementedError()


if typing.TYPE_CHECKING:

    class FieldDict(ValueBase[Dict[K, S]]):
        def __getitem__(self, item: K) -> Type[S]:
            raise NotImplementedError()

else:

    class FieldDict(Field[Dict[K, S]]):
        def __getitem__(self, item: K) -> Type[S]:
            raise NotImplementedError()


class FieldBase(ValueBase[T]):
    _parent: Any
    _lock: threading.RLock

    def __init__(self, parent: "ValueBase"):
        super().__init__()  # type: ignore
        self._parent = parent
        parent = parent
        self._lock = parent.lock
        while not isinstance(parent, ValueBase):
            parent = parent.parent
        self._root = parent
        assert isinstance(self._root, ValueBase)

    @property
    def lock(self) -> threading.RLock:
        return self._lock

    @property
    def fields(self):
        return self

    def __getattr__(self, key):
        if key in ["get", "set", "subscribe", "subscribe_change", "value", "use_value", "use", "use_state", "fields", "update", "lock"] or key.startswith("_"):
            if key in self.__dict__:
                return self.__dict__[key]
            return super().__getattribute__(key)
            # return getattr(type(self), key)
        obj = self.get()
        try:
            if isinstance(getattr(type(obj), key), Field):
                return FieldAttrField(self, key)
        except AttributeError:
            pass
        return FieldAttr(self, key)

    def subscribe(self, listener: Callable[[T], None]):
        def on_change(new, old):
            new_value = self.get(new)
            old_value = self.get(old)
            if not equals(new_value, old_value):
                listener(new_value)

        return self._root.subscribe_change(on_change)

    def subscribe_change(self, listener: Callable[[T, T], None]):
        def on_change(new, old):
            new_value = self.get(new)
            old_value = self.get(old)
            if new_value != old_value:
                listener(new_value, old_value)

        return self._root.subscribe_change(on_change)

    def __getitem__(self, key):
        return FieldItem(self, key)

    def get(self, obj=None):
        raise NotImplementedError

    def set(self, value):
        raise NotImplementedError


class FieldRoot(FieldBase):
    def __init__(self, state: ValueBase):
        super().__init__(state)

    def get(self, obj=None):
        # we are at the root, so override the object
        # so we can get the 'old' value
        if obj is not None:
            return obj
        return self._parent.get()

    def set(self, value):
        self._parent.set(value)


class FieldAttr(FieldBase):
    def __init__(self, parent: ValueBase, key: str):
        self.key = key
        super().__init__(parent)

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
    def __init__(self, parent: ValueBase, key: str):
        self.key = key
        super().__init__(parent)

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


class FieldAttrField(FieldBase):
    # similar to FieldAttr, but uses __dict__ to bypass the Field descriptor
    def __init__(self, parent: ValueBase, key: str):
        self.key = key
        super().__init__(parent)

    def get(self, obj=None):
        obj = self._parent.get(obj)
        return obj.__dict__[self.key]

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


def Ref(x: T):
    return cast(Field[T], x)


def reactive(value: S) -> Reactive[S]:
    return Reactive(value)
