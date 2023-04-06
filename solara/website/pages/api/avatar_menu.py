"""
# AvatarMenu

"""
from solara_enterprise import auth

from solara.website.utils import apidoc

from . import NoPage

title = "AvatarMenu"

Page = NoPage


__doc__ += apidoc(auth.AvatarMenu.f)  # type: ignore
