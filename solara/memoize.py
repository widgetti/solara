import logging

from diskcache import Cache

logger = logging.getLogger("solara.memoize")

try:
    cache = Cache()
except:  # noqa
    # on digital ocean for example, we get sqlite3.OperationalError: disk I/O error
    logger.warning("Could not create diskcache, memoization will not work")

    def identity(name=None, typed=False, expire=None, tag=None, ignore=()):
        def f(func):
            return func

        return f

    memoize = identity
else:
    memoize = cache.memoize
