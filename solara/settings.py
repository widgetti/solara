import os
from typing import Optional

import solara.util

from .minisettings import BaseSettings, Field
from .util import get_solara_home

try:
    import dotenv
except ImportError:
    pass
else:
    dotenv.load_dotenv()


home = get_solara_home()
if not home.exists():
    try:
        home.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass  # can fail in for instance docker when $HOME is not set/writable


class Cache(BaseSettings):
    type: str = Field("memory", env="SOLARA_CACHE", title="Type of cache, e.g. 'memory', 'disk', 'redis', or a multilevel cache, e.g. 'memory,disk'")
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


# in colab or vscode there is not solara cdn proxy available
_should_use_proxy = not (solara.util.is_running_in_colab() or solara.util.is_running_in_vscode() or solara.util.is_running_in_voila())


class Assets(BaseSettings):
    cdn: str = "https://cdn.jsdelivr.net/npm/"
    proxy: bool = _should_use_proxy

    class Config:
        env_prefix = "solara_assets_"
        case_sensitive = False
        env_file = ".env"


class MainSettings(BaseSettings):
    check_hooks: str = "warn"
    allow_reactive_boolean: bool = True
    # TODO: also change default_container in solara/components/__init__.py
    default_container: Optional[str] = "Column"
    allow_global_context: bool = True

    class Config:
        env_prefix = "solara_"
        case_sensitive = False
        env_file = ".env"


class Storage(BaseSettings):
    mutation_detection: Optional[bool] = None  # True/False, or None to auto determine
    factory: str = "solara.toestand.default_storage"
    init_lock_timeout: float = Field(
        2.0,
        title="Seconds to wait for a reactive variable's initialization lock before logging a possible-deadlock warning (<=0 or NaN disables the warning and waits indefinitely)",
    )
    init_lock_warning_cooldown: float = Field(
        60.0,
        title="Minimum seconds between repeated initialization-lock timeout warnings for the same reactive variable",
    )

    def get_factory(self):
        return solara.util.import_item(self.factory)

    class Config:
        env_prefix = "solara_storage_"
        case_sensitive = False
        env_file = ".env"


assets: Assets = Assets()
cache: Cache = Cache()
main = MainSettings()
storage = Storage()

if main.check_hooks not in ["off", "warn", "raise"]:
    raise ValueError(f"Invalid value for check_hooks: {main.check_hooks}, expected one of ['off', 'warn', 'raise']")


def __getattr__(name):
    # `state` (state persistence) is defined in solara.server.settings - it is a server-only
    # feature and its knobs are coupled to server siblings (kernel.cull_timeout,
    # session.secret_key, main.mode) - but it stays reachable as solara.settings.state too.
    # PEP 562 keeps the import lazy so this module never eagerly pulls in server modules.
    if name == "state":
        import solara.server.settings

        return solara.server.settings.state
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
