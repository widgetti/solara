"""
# AvatarMenu

"""
try:
    from solara_enterprise import auth
except ImportError:
    auth = None
from solara.website.utils import apidoc

from . import NoPage

title = "AvatarMenu"

Page = NoPage


if auth:
    __doc__ += apidoc(auth.AvatarMenu.f)  # type: ignore
else:
    __doc__ += "solara-enterprise not installed."
