from typing import Any, Callable, Optional

import redis
import solara.settings

from solara_enterprise.cache.base import Base, make_key


class Redis(Base):
    """Wraps a client such that the values are pickled/unpickled"""

    def __init__(
        self, client: Optional[redis.Redis] = None, clear=solara.settings.cache.clear, prefix=b"solara:cache:", make_key: Callable[[Any], bytes] = make_key
    ):
        self.client = client or redis.Redis()
        super().__init__(self.client, prefix=prefix, clear=clear, make_key=make_key)

    def clear(self):
        with self.client.lock(b"lock:" + self.prefix):
            keys = self.keys()
            for key in keys:
                del self[key]

    def keys(self):
        return self.client.keys(self.prefix + b"*")
