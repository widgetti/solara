import os
import importlib
import re
import site
import sys
import uuid
import warnings
from enum import Enum
from pathlib import Path
from typing import Optional, List

try:
    from filelock import FileLock
except ModuleNotFoundError:
    FileLock = None  # type: ignore

import solara.util
from solara.minisettings import BaseSettings

from .. import (  # noqa  # sidefx is that this module creates the ~/.solara directory
    settings,
)
from ..util import get_solara_home

if site.getuserbase() and __file__.startswith(site.getuserbase()):
    prefix = site.getuserbase()
else:
    prefix = sys.prefix


class ThemeVariant(str, Enum):
    light = "light"
    dark = "dark"
    auto = "auto"


class ThemeSettings(BaseSettings):
    variant: ThemeVariant = ThemeVariant.light
    loader: str = "solara"
    show_banner: bool = True

    class Config:
        env_prefix = "solara_theme_"
        case_sensitive = False
        env_file = ".env"


class SSG(BaseSettings):
    # the first app create will initialize this if it is not set
    build_path: Optional[Path] = None
    enabled: bool = False
    headed: bool = False

    class Config:
        env_prefix = "solara_ssg_"
        case_sensitive = False
        env_file = ".env"


class Search(BaseSettings):
    enabled: bool = False

    class Config:
        env_prefix = "solara_search_"


class Telemetry(BaseSettings):
    mixpanel_token: str = "91845eb13a68e3db4e58d64ad23673b7"
    mixpanel_enable: bool = True
    server_user_id: str = "not_set"
    server_fingerprint: str = str(uuid.getnode())
    server_session_id: str = str(uuid.uuid4())

    class Config:
        env_prefix = "solara_telemetry_"
        case_sensitive = False
        env_file = ".env"


class Assets(BaseSettings):
    proxy_cache_dir: Path = Path(prefix + "/share/solara/cdn/")
    fontawesome_enabled: bool = True
    fontawesome_path: str = "/font-awesome@4.5.0/css/font-awesome.min.css"
    extra_locations: List[str] = []

    def extra_paths(self) -> List[Path]:
        # translate locations (packages, directories) into list of paths
        paths = []
        for location in self.extra_locations:
            if Path(location).exists():
                paths.append(Path(location))
            else:
                try:
                    package = importlib.import_module(location)
                except ModuleNotFoundError:
                    raise RuntimeError(f"Could not find {location} as a file or package (SOLARA_ASSETS_EXTRA_LOCATION={self.extra_locations!r}) ")
                if not hasattr(package, "__path__"):
                    raise RuntimeError(f"{location} is not a package (SOLARA_ASSETS_EXTRA_LOCATION={self.extra_locations!r}) ")
                paths.append(Path(package.__path__[0]))
        return paths

    class Config:
        env_prefix = "solara_assets_"
        case_sensitive = False
        env_file = ".env"


class Kernel(BaseSettings):
    cull_timeout: str = "24h"
    max_count: Optional[int] = None
    threaded: bool = solara.util.has_threads

    class Config:
        env_prefix = "solara_kernel_"
        case_sensitive = False
        env_file = ".env"


AUTH0_TEST_CLIENT_ID = "cW7owP5Q52YHMZAnJwT8FPlH2ZKvvL3U"
AUTH0_TEST_CLIENT_SECRET = "zxITXxoz54OjuSmdn-PluQgAwbeYyoB7ALlnLoodftvAn81usDXW0quchvoNvUYD"
AUTH0_TEST_API_BASE_URL = "dev-y02f2bpr8skxu785.us.auth0.com"
AUTH0_LOGOUT_PATH = "v2/logout"

FIEF_TEST_CLIENT_ID = "x2np62qgwp6hnEGTP4JYUE3igdZWhT-AvjpjwwDyKXU"
FIEF_TEST_CLIENT_SECRET = "XQlByE1pVIz5h2SBN2GYDwT_ziqArHJgLD3KqMlCHjg"
FIEF_TEST_API_BASE_URL = "solara-dev.fief.dev"
FIEF_LOGOUT_PATH = "logout"
SESSION_SECRET_KEY_DEFAULT = "change me"

OAUTH_TEST_CLIENT_IDs = [AUTH0_TEST_CLIENT_ID, FIEF_TEST_CLIENT_ID]


class Session(BaseSettings):
    secret_key: str = SESSION_SECRET_KEY_DEFAULT
    http_only: bool = False
    https_only: Optional[bool] = None
    same_site: str = "lax"

    class Config:
        env_prefix = "solara_session_"
        case_sensitive = False
        env_file = ".env"


class OAuth(BaseSettings):
    private: bool = False

    client_id: str = AUTH0_TEST_CLIENT_ID
    client_secret: str = AUTH0_TEST_CLIENT_SECRET
    api_base_url: str = AUTH0_TEST_API_BASE_URL
    logout_path: str = AUTH0_LOGOUT_PATH
    scope: str = "openid profile email"

    class Config:
        env_prefix = "solara_oauth_"
        case_sensitive = False
        env_file = ".env"


HOST_DEFAULT = os.environ.get("HOST", "localhost")
is_mac_os_conda = "arm64-apple-darwin" in HOST_DEFAULT
is_wsl_windows = re.match(r".*?-w1[0-9]", HOST_DEFAULT)
if is_mac_os_conda or is_wsl_windows:
    HOST_DEFAULT = "localhost"


class Server(BaseSettings):
    ignore_nbextensions: List[str] = []

    class Config:
        env_prefix = "solara_server_"
        case_sensitive = False
        env_file = ".env"


class MainSettings(BaseSettings):
    use_pdb: bool = False
    mode: str = "production"
    tracer: bool = False
    timing: bool = False
    root_path: Optional[str] = None  # e.g. /myapp (without trailing slash)
    base_url: str = ""  # e.g. https://myapp.solara.run/myapp/
    platform: str = sys.platform
    host: str = HOST_DEFAULT
    experimental_performance: bool = False

    class Config:
        env_prefix = "solara_"
        case_sensitive = False
        env_file = ".env"


main = MainSettings()
server = Server()
theme = ThemeSettings()
telemetry = Telemetry()
ssg = SSG()
search = Search()
assets = Assets()
oauth = OAuth()
session = Session()
kernel = Kernel()
# fail early
solara.util.parse_timedelta(kernel.cull_timeout)

if settings.assets.proxy:
    try:
        assets.proxy_cache_dir.mkdir(exist_ok=True, parents=True)
    except OSError as e:
        settings.assets.proxy = False
        warnings.warn(
            f"Could not create {assets.proxy_cache_dir} due to {e}. We will automatically disable the assets proxy for you. "
            "If you want to disable this warning, set SOLARA_ASSETS_PROXY to False (e.g. export SOLARA_ASSETS_PROXY=false). "
            "Or change the SOLARA_PROXY_CACHE_DIR environment variable to a directory where you have write access."
        )
        # that's ok, the user probably doesn't have permission to create the directory
        # in this case, we would need to install solara-assets?
        pass

if telemetry.server_user_id == "not_set" and FileLock is not None:
    home = get_solara_home()
    server_user_id_file = home / "server_user_id.txt"
    try:
        with FileLock(str(server_user_id_file) + ".lock"):
            if not server_user_id_file.exists():
                server_user_id_file.write_text(str(uuid.uuid4()))
            telemetry.server_user_id = server_user_id_file.read_text()
    except OSError:
        pass  # it's ok

if oauth.client_id:
    if oauth.client_id not in OAUTH_TEST_CLIENT_IDs:
        if session.secret_key == SESSION_SECRET_KEY_DEFAULT:
            raise ValueError(
                "You must set a session secret key for oauth, it is not safe to use the default. Please set SOLARA_SESSION_SECRET_KEY in your environment."
            )
        if session.https_only is None:
            raise ValueError(
                "You must set https_only for the session to True (recommended) or False in your are using your own oauth provider."
                "Please set SOLARA_SESSION_HTTPS_ONLY in your environment to True or False"
            )
    else:
        # for the test accounts, this is fine
        if session.https_only is None:
            session.https_only = False


# call early so a misconfiguration fails early
assets.extra_paths()
