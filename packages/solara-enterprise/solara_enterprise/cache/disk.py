import logging
import shutil
from typing import MutableMapping

import diskcache
import solara.settings
import solara.util

logger = logging.getLogger("solara-enterprise.cache.disk")


class Disk(MutableMapping):
    def __init__(
        self,
        clear=False,
        max_size=solara.settings.cache.disk_max_size,
        path=solara.settings.cache.path,
    ):
        # same as solara.cache.Memory
        eviction_policy = "least-recently-used"
        max_size = solara.util.parse_size(max_size)
        if clear:
            try:
                logger.debug("Clearing disk cache: %s", path)
                shutil.rmtree(path)
            except OSError:  # Windows wonkiness
                logger.exception(f"Error clearing disk cache: {path}")

        self.diskcache = diskcache.Cache(path, size_limit=max_size, eviction_policy=eviction_policy)

    def __getitem__(self, key):
        return self.diskcache[key]

    def __setitem__(self, key, value):
        self.diskcache[key] = value

    def __delitem__(self, key):
        del self.diskcache[key]

    def __iter__(self):
        return iter(self.diskcache)

    def __len__(self):
        return len(self.diskcache)
