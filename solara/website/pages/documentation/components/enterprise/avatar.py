"""
# Avatar

"""

from types import ModuleType
from typing import Optional

auth: Optional[ModuleType]
try:
    from solara_enterprise import auth
except ImportError:
    auth = None
from solara.website.components import NoPage
from solara.website.utils import apidoc

title = "Avatar"

Page = NoPage

if auth:
    __doc__ += apidoc(auth.Avatar.f)  # type: ignore
else:
    __doc__ += "solara-enterprise not installed."
