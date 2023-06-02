# Caching

Solara has a dict-like object at `solara.cache.storage` that can be used to store objects in under a key. So we can use this global
object as normal dict, e.g.:

```python
import solara
solara.cache.storage["my-key"] = expensive_function_call()
assert "my-key" in solara.cache.storage
```

Note that at any time later on, the key may be removed from this object, as a cache always has a limited capacity.

The `solara.cache.storage` cache object is used by [memoize](/api/memoize), if no storage argument is passed to this decorator.

## Types of cache

Solara core comes by default with an in-memory cache using a [LRU](https://en.wikipedia.org/wiki/Cache_replacement_policies#Least_recently_used_(LRU)) (Least recently used) strategy. When the
cache becomes too full, this removes entries used least recently.

The cache is set by default to:
```python
solara.cache.storage = solara.cache.Memory(maxsize=128)
```

Which will remove the least recently used element when the 129th item is added.

The memory cache is also configurable using environment variable:
```
$ export SOLARA_CACHE=memory  # already the default
$ export SOLARA_CACHE_MEMORY_MAX_ITEMS=128  # already the default
```

## Custom caches
An infinite cache can be set using:

```python
solara.cache.storage = {}  # a regular dict
```

The [cachetools](https://cachetools.readthedocs.io/) project has some caching types that behave like a Python dict, and are compatible with Solara, e.g.:

```python
import cachetools
import solara
solara.cache.storage = cachetools.FIFOCache(maxsize=100)
```

## Solara-enterprise

With solara-enterprise, we have more cache storage options.

### Memory (byte size based)

The cache will limit the total number of bytes to a set maximum, instead of the number of items as is with the normal 'memory' cache.

This can be set using code:

```python
import solara
solara.cache.configure("memory-size")
# or more explicit
import solara_enterprise.cache.memory_size
solara.cache.storage = solara_enterprise.cache.memory_size.MemorySize(
    max_size="1GB"  # already the default
)
```

The 'memory-size' cache can also be configured using environment variables:

```
$ export SOLARA_CACHE=memory-size
$ export SOLARA_CACHE_MEMORY_MAX_SIZE=1GB  # already the default

```


### Disk cache

This cache will persist the entries to disk, allowing multiple processes to share the same data. This cache type is ideal when using multiple workers on a single node.

This can be set using code:

```python
import solara
solara.cache.configure("disk")
# or more explicit
import solara_enterprise.cache.disk
solara.cache.storage = solara_enterprise.cache.disk.Disk(
    max_size="10GB", path="/home/maarten/.solara/cache"  # already the default
)
```

Or configurable using environment variable:
```
$ export SOLARA_CACHE=disk
$ export SOLARA_CACHE_DISK_MAX_SIZE=10GB  # already the default
$ export SOLARA_CACHE_PATH_=/home/maarten/.solara/cache  # already the default
```

### Redis cache

This cache will store the entries in a [Redis](https://redis.io/) server, allowing multiple nodes to share the same data. This is ideal in a cluster/distributed configuration.

This can be set using code:

```python
import solara
solara.cache.configure("redis")
# or more explicit
import solara_enterprise.cache.redis
# optionally pass in a redis.Client object
solara.cache.storage = solara_enterprise.cache.redis.Redis()
```

Or configured using environment variable:
```
$ export SOLARA_CACHE=redis
```

### Multi-level cache

We can chain a few caches to get a multilevel cache. This allows us to get the benefits of the low latency memory cache while sharing it with other workers and nodes.

```python
import solara
solara.cache.configure("memory,disk,redis")
# or more explicit
import solara_enterprise.cache.multi_level
import solara_enterprise.cache.disk
import solara_enterprise.cache.redis
l1 = solara.cache.Memory()
l2 = solara_enterprise.cache.disk.Disk()
l3 = solara_enterprise.cache.redis.Redis()
solara.cache.storage = solara_enterprise.cache.multi_level.MultiLevel(
    l1, l2, l3
)
```

Or configured using an environment variable:
```
$ export SOLARA_CACHE="memory,disk,redis"
```
