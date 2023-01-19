import os
from typing import Optional

import pydantic
from pydantic import Field

from .util import get_solara_home

home = get_solara_home()
if not home.exists():
    home.mkdir(parents=True, exist_ok=True)


class Cache(pydantic.BaseSettings):
    type: str = pydantic.Field("memory", env="SOLARA_CACHE", title="Type of cache, e.g. 'memory', 'disk', 'redis', or a multilevel cache, e.g. 'memory,disk'")
    disk_max_size: str = Field("10GB", title="Maximum size for'disk' cache , e.g. 10GB, 500MB")
    memory_max_size: str = Field("1GB", title="Maximum size for 'memory-size' cache, e.g. 10GB, 500MB")
    memory_max_items: int = Field(128, title="Maximum number of items for 'memory' cache")
    clear: bool = Field(False, title="Clear the cache on startup, only applies to disk and redis caches")
    path: Optional[str] = Field(
        os.path.join(home, "cache"), env="SOLARA_CACHE_PATH", title="Storage location for 'disk' cache. Defaults to `${SOLARA_HOME}/cache`"
    )

    class Config:
        env_prefix = "solara_cache_"
        case_sensitive = False
        env_file = ".env"


cache: Cache = Cache()
