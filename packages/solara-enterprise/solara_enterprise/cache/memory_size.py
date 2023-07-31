import logging
import pickle
from typing import Any, Callable, MutableMapping

from cachetools import LRUCache
from solara_enterprise.cache.base import Base, make_key

import solara.settings
import solara.util

logger = logging.getLogger("solara-enterprise.cache.memory")


def sizeof(obj):
    size = len(pickle.dumps(obj))
    logger.debug("size of %s: %s", obj, size)
    return size


class MemorySize(Base):
    def __init__(
        self,
        max_size=solara.settings.cache.memory_max_size,
        make_key: Callable[[Any], bytes] = make_key,
        sizeof: Callable[[Any], int] = sizeof,
    ):
        maxsize = solara.util.parse_size(max_size)
        _wrapper_dict: MutableMapping[bytes, bytes] = LRUCache(maxsize=maxsize, getsizeof=sizeof)
        super().__init__(_wrapper_dict, make_key=make_key)
