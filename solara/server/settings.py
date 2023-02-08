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

if __file__.startswith(site.getuserbase()):
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


class MainSettings(pydantic.BaseSettings):
    use_pdb: bool = False
    mode: str = "production"
    tracer: bool = False
    timing: bool = False
    root_path: Optional[str] = None

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

assets.proxy_cache_dir.mkdir(exist_ok=True, parents=True)

if telemetry.server_user_id == "not_set":
    home = get_solara_home()
    server_user_id_file = home / "server_user_id.txt"
    with FileLock(str(server_user_id_file) + ".lock"):
        if not server_user_id_file.exists():
            server_user_id_file.write_text(str(uuid.uuid4()))
        telemetry.server_user_id = server_user_id_file.read_text()
