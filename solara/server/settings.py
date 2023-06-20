import site
import sys
import uuid
from enum import Enum
from pathlib import Path
from typing import Optional

import pydantic
from filelock import FileLock

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


class ThemeSettings(pydantic.BaseSettings):
    variant: ThemeVariant = ThemeVariant.light
    variant_user_selectable: bool = True
    loader: str = "solara"

    class Config:
        env_prefix = "solara_theme_"
        case_sensitive = False
        env_file = ".env"


class SSG(pydantic.BaseSettings):
    # the first app create will initialize this if it is not set
    build_path: Optional[Path] = None
    enabled: bool = False
    headed: bool = False

    class Config:
        env_prefix = "solara_ssg_"
        case_sensitive = False
        env_file = ".env"


class Search(pydantic.BaseSettings):
    enabled: bool = False


class Telemetry(pydantic.BaseSettings):
    mixpanel_token: str = "91845eb13a68e3db4e58d64ad23673b7"
    mixpanel_enable: bool = True
    server_user_id: str = "not_set"
    server_fingerprint: str = str(uuid.getnode())
    server_session_id: str = str(uuid.uuid4())

    class Config:
        env_prefix = "solara_telemetry_"
        case_sensitive = False
        env_file = ".env"


class Assets(pydantic.BaseSettings):
    cdn: str = "https://cdn.jsdelivr.net/npm/"
    proxy: bool = True
    proxy_cache_dir: Path = Path(prefix + "/share/solara/cdn/")
    fontawesome_enabled: bool = True
    fontawesome_path: str = "/font-awesome@4.5.0/css/font-awesome.min.css"

    class Config:
        env_prefix = "solara_assets_"
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


class Session(pydantic.BaseSettings):
    secret_key: str = SESSION_SECRET_KEY_DEFAULT
    https_only: Optional[bool] = None
    same_site: str = "lax"

    class Config:
        env_prefix = "solara_session_"
        case_sensitive = False
        env_file = ".env"


class OAuth(pydantic.BaseSettings):
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


class MainSettings(pydantic.BaseSettings):
    use_pdb: bool = False
    mode: str = "production"
    tracer: bool = False
    timing: bool = False
    root_path: Optional[str] = None  # e.g. /myapp/
    base_url: str = ""  # e.g. https://myapp.solara.run/myapp/
    platform: str = sys.platform

    class Config:
        env_prefix = "solara_"
        case_sensitive = False
        env_file = ".env"


main = MainSettings()
theme = ThemeSettings()
telemetry = Telemetry()
ssg = SSG()
search = Search()
assets = Assets()
oauth = OAuth()
session = Session()

assets.proxy_cache_dir.mkdir(exist_ok=True, parents=True)

if telemetry.server_user_id == "not_set":
    home = get_solara_home()
    server_user_id_file = home / "server_user_id.txt"
    with FileLock(str(server_user_id_file) + ".lock"):
        if not server_user_id_file.exists():
            server_user_id_file.write_text(str(uuid.uuid4()))
        telemetry.server_user_id = server_user_id_file.read_text()

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
