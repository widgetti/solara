import threading
from abc import abstractmethod
from typing import Any, Callable, Dict, List, MutableMapping
from warnings import warn

ObserverCallback = Callable[[Any, Any], None]


class MutableMappingBase(MutableMapping):
    @abstractmethod
    def _get_dict(self) -> MutableMapping:
        pass

    def __delitem__(self, key) -> None:
        self._get_dict().__delitem__(key)

    def __getitem__(self, key):
        return self._get_dict().__getitem__(key)

    def __iter__(self):
        return self._get_dict().__iter__()

    def __len__(self):
        return self._get_dict().__len__()

    def __setitem__(self, key, value):
        self._get_dict().__setitem__(key, value)


class ObservableMutableMapping(MutableMappingBase):
    # list of observers for each key
    observers: Dict[Any, List[ObserverCallback]]

    def __init__(self) -> None:
        super().__init__()
        self.observers = {}
        self.lock = threading.Lock()

    def subscribe_key(self, key, callback: ObserverCallback):
        if key not in self.observers:
            with self.lock:
                if key not in self.observers:
                    self.observers[key] = []
        self.observers[key].append(callback)
        if self.observers[key].count(callback) > 1:
            warn("Callback already subscribed")

        def unsubscribe():
            self.observers[key].remove(callback)

        return unsubscribe

    def trigger_key(self, key):
        for callback in self.observers[key]:
            callback(key, self[key])
