import dataclasses
from typing import Any, Callable, Generic, List, Set, TypeVar, Union, cast

import react_ipywidgets as react

from solara.scope.types import ObservableMutableMapping

T = TypeVar("T")
S = TypeVar("S")  # used for state


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


def merge_state(d1: S, **kwargs):
    if dataclasses.is_dataclass(d1):
        return dataclasses.replace(d1, **kwargs)
    return cast(S, {**cast(dict, d1), **kwargs})


class Storage(Generic[T]):
    def __init__(self, initial_state: T, merge: Callable[..., T] = merge_state):
        self.initial_state = initial_state
        self.merge = merge
        self.listeners: Set[Callable[[T], None]] = set()

    def subscribe(self, listener: Callable[[T], None]):
        self.listeners.add(listener)

        def cleanup():
            self.listeners.remove(listener)

        return cleanup

    def update(self, **kwargs):
        self.set(self.merge(self.get(), **kwargs))

    def set(self, new_state: T):
        raise NotImplementedError

    def get(self) -> T:
        raise NotImplementedError

    def fire(self, state: T):
        for listener in self.listeners:
            listener(state)


class SubStorage(Storage):
    def __init__(self, storage: Storage, key):
        self.storage = storage
        self.key = key

    def subscribe(self, listener: Callable[[T], None]):
        return self.storage.subscribe(lambda state: listener(state[self.key]))

    def update(self, **kwargs):
        new_value = self.storage.merge(self.get(), **kwargs)
        self.storage.update(**{self.key: new_value})

    def set(self, new_state: T):
        # TODO: use merge
        self.storage.update(**{self.key: new_state})

    def get(self) -> T:
        raise NotImplementedError


class SubStorageDict(SubStorage):
    def get(self) -> T:
        return self.storage.get()[self.key]


class SubStorageAttr(SubStorage):
    def get(self) -> T:
        return getattr(self.storage.get(), self.key)


class StorageGlobal(Storage[T]):
    def __init__(self, initial_state: T, merge: Callable[..., T] = merge_state):
        super().__init__(initial_state, merge=merge)
        self.state = self.initial_state

    def set(self, new_state: T):
        self.state = new_state
        self.fire(self.state)

    def get(self):
        return self.state


ObserverCallback = Callable[[Any, Any], None]


class StorageObserableMutableMapping(Storage[T]):
    """Storage that subscribes to changes in an ObservableMutableMapping"""

    def __init__(self, initial_state: T, key: str, observable_dict: ObservableMutableMapping, merge: Callable[..., T] = merge_state):
        self.key = key
        super().__init__(initial_state, merge=merge)
        self.observable_dict = observable_dict
        self.observable_dict.subscribe_key(self.key, self.on_external_change)
        if self.key not in self.observable_dict:
            self.observable_dict[self.key] = self.initial_state
            self.state = self.initial_state
        else:
            self.state = self.observable_dict[self.key]

    def get(self):
        return self.observable_dict.get(self.key, self.initial_state)

    def set(self, new_state: T):
        self.observable_dict[self.key] = new_state
        self.fire(new_state)

    def on_external_change(self, key, value):
        assert key == self.key
        self.fire(value)

    def delete(self):
        del self.observable_dict[self.key]


class Store(Generic[S]):
    _storage: Storage[S]

    def __init__(self, default_value: S = None, storage: Union[Storage[S], ObservableMutableMapping] = None):
        cls = type(self)
        self.storage_key = cls.__module__ + ":" + cls.__name__
        if storage is None:
            if default_value is None:
                raise ValueError("Provide default_value or storage")
            import solara.scope

            storage = StorageObserableMutableMapping[S](default_value, self.storage_key, solara.scope.connection)
        if isinstance(storage, ObservableMutableMapping):
            if default_value is None:
                raise ValueError("Provide default_value or storage")
            storage = StorageObserableMutableMapping[S](default_value, self.storage_key, storage)
        self._storage = storage
        self.__post__init__(storage)

    def __post__init__(self, storage: Storage[S]):
        pass

    def update(self, **kwargs):
        self._storage.update(**kwargs)

    def set(self, new_state: S):
        self._storage.set(new_state)

    def get(self) -> S:
        return self._storage.get()

    def subscribe(self, listener: Callable[[S], None]):
        return self._storage.subscribe(listener)

    def use(self, selector: Callable[[S], T]) -> T:
        slice = use_sync_external_store_with_selector(
            self.subscribe,
            self.get,
            selector,
        )
        return slice

    @property
    def props(self) -> S:
        # we lie about the return type, but in combination with
        # setter we can make type safe setters (see docs/tests)
        return cast(S, Prop(self, []))

    def setter(self, value: T) -> Callable[[T], None]:
        prop = cast(Prop, value)
        assert len(prop.key) == 1

        def setter(new_value: T):
            self.update(**{prop.key[0]: new_value})

        return cast(Callable[[T], None], setter)


class Prop:
    def __init__(self, store: Store, key: List["str"] = []):
        self.store = store
        self.key = key

    def __getattr__(self, key):
        return Prop(self.store, self.key + [key])
