"""
# Avatar

"""
from solara_enterprise import auth

from solara.website.utils import apidoc

from . import NoPage

title = "Avatar"

Page = NoPage


__doc__ += apidoc(auth.Avatar.f)  # type: ignore
