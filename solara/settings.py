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


class State(BaseSettings):
    backend: str = ""  # "" = disabled; a name in solara.state.state_backend_map ("redis", "memory", ...)
    url: str = ""  # backend DSN, e.g. "redis://localhost:6379/0"
    secret_keys: str = ""  # comma-separated HMAC keys; verify-any, sign-first (rotation). REQUIRED when enabled
    allow_pickle: bool = False  # deployer gate; the "pickle" codec raises without it
    ttl: Optional[str] = None  # default: kernel.cull_timeout
    orphan_cull_timeout: str = "5m"  # applies only with a shared backend
    prefix: str = "solara:state:"  # key prefix / table name, backend-interpreted
    flush_debounce: str = "300ms"
    connect_timeout: float = 0.3  # hard cap on takeover/flush blocking
    breaker_failures: int = 3  # circuit breaker: consecutive failures to open
    breaker_window: str = "30s"  # open duration before a half-open probe
    schema_tag: str = ""  # state-schema tag ("" -> derived); mismatch => clean state reset
    auto_remount: Optional[bool] = None  # None: on iff backend set; can force on/off
    bailout_storm_threshold: float = 0.5  # bail-out rate valve
    test_eviction: bool = False  # dev/test-only kernel-eviction route gate (§6.4); refused in production

    def secret_key_list(self):
        # secret_keys is a comma-separated env value; minisettings has no native List type here
        return [key.strip() for key in self.secret_keys.split(",") if key.strip()]

    class Config:
        env_prefix = "solara_state_"
        case_sensitive = False
        env_file = ".env"


assets: Assets = Assets()
cache: Cache = Cache()
main = MainSettings()
storage = Storage()
state = State()

if main.check_hooks not in ["off", "warn", "raise"]:
    raise ValueError(f"Invalid value for check_hooks: {main.check_hooks}, expected one of ['off', 'warn', 'raise']")
