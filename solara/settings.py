import os
from typing import Optional

import pydantic
from pydantic import Field

# BaseSettings : Optional[ClassVar] = None
# with pydantic 2.0, we require pydantic_settings
try:
    import pydantic_settings
except ModuleNotFoundError:
    # we should be on pydantic 1.x
    BaseSettings = pydantic.BaseSettings
else:
    major = pydantic_settings.__version__.split(".")[0]
    if major != "0":
        # but the old pydantic_settings is unrelated
        BaseSettings = pydantic_settings.BaseSettings
    else:
        # we should be on pydantic 2.x
        BaseSettings = pydantic.BaseSettings


from .util import get_solara_home

home = get_solara_home()
if not home.exists():
    home.mkdir(parents=True, exist_ok=True)


class Cache(BaseSettings):  # type: ignore
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
