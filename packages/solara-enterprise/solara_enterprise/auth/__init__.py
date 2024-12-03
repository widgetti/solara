from typing import Dict, Optional, cast

from solara.lab import Reactive

from .components import Avatar, AvatarMenu
from .utils import get_login_url, get_logout_url

__all__ = ["user", "get_login_url", "get_logout_url", "Avatar", "AvatarMenu"]

# the current way of generating a key is based in the default value
# which may collide after a hot reload, since solara itself is not reloaded
# if we give a fixed key, we can avoid this
user = Reactive(cast(Optional[Dict], None), key="solara-enterprise.auth.user")
