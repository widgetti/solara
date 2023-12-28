import hashlib
import pickle
import sys
from typing import Any, Callable, MutableMapping


def make_key(object):
    """Generates a key by pickling the object, and generating an md5 hash of the pickled object.

    Primitive objects such as short (<100 length) strings and ints are not pickled, and are used as is.
    """
    if isinstance(object, str) and len(object) < 100:
        return object.encode("utf-8")
    elif isinstance(object, int):
        return str(object).encode("utf-8")
    else:
        bytes = pickle.dumps(object)
        if sys.version_info[:2] < (3, 9):
            return hashlib.md5(bytes).digest()
        else:
            return hashlib.md5(bytes, usedforsecurity=False).digest()  # type: ignore


class Base(MutableMapping):
    def __init__(self, wrapper_dict, clear=False, prefix=b"", make_key: Callable[[Any], bytes] = make_key):
        assert wrapper_dict is not None
        self._wrapper_dict = wrapper_dict
        self._make_key = make_key
        self.prefix = prefix
        if clear:
            self.clear()

    def generate_key(self, key) -> bytes:
        return self.prefix + bytes(self._make_key(key))

    def __getitem__(self, key):
        if isinstance(key, bytes) and key.startswith(self.prefix):
            wrapper_key = key
        else:
            wrapper_key = self.generate_key(key)
        return pickle.loads(self._wrapper_dict[wrapper_key])  # type: ignore

    def __setitem__(self, key, value):
        if isinstance(key, bytes) and key.startswith(self.prefix):
            wrapper_key = key
        else:
            wrapper_key = self.generate_key(key)
        self._wrapper_dict[wrapper_key] = pickle.dumps(value)

    def __delitem__(self, key):
        if isinstance(key, bytes) and key.startswith(self.prefix):
            wrapper_key = key
        else:
            wrapper_key = self.generate_key(key)
        del self._wrapper_dict[wrapper_key]

    def __iter__(self):
        return iter(self.keys())

    def __len__(self):
        return len(self.keys())

    def keys(self):
        return self._wrapper_dict.keys()
