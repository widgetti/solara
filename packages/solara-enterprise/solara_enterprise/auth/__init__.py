from typing import Dict, Optional, cast

from solara.lab import Reactive

from .components import Avatar, AvatarMenu
from .utils import get_login_url, get_logout_url

__all__ = ["user", "get_login_url", "get_logout_url", "Avatar", "AvatarMenu"]

user = Reactive(cast(Optional[Dict], None))
