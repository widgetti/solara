"""
# AvatarMenu

"""

from types import ModuleType
from typing import Optional

auth: Optional[ModuleType] = None
try:
    from solara_enterprise import auth as enterprise_auth

    auth = enterprise_auth
except ImportError:
    pass
from solara.website.components import NoPage
from solara.website.utils import apidoc

title = "AvatarMenu"

Page = NoPage


if auth:
    __doc__ += apidoc(auth.AvatarMenu.f)  # type: ignore
else:
    __doc__ += "solara-enterprise not installed."
