"""
# AppBar

"""

import solara
import solara.lab
from solara.website.components import NoPage
from solara.website.utils import apidoc

title = "AppBar"

Page = NoPage


__doc__ += apidoc(solara.AppBar.f)  # type: ignore
