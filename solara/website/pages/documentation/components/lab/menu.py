"""
# Menus

This page contains the various kinds of menu elements available to use in solara

# Menu
"""

import solara
from solara.website.components import NoPage
from solara.website.utils import apidoc

title = "Menus"


__doc__ += apidoc(solara.lab.components.menu.Menu.f)  # type: ignore
__doc__ += "# ClickMenu"
__doc__ += apidoc(solara.lab.components.menu.ClickMenu.f)  # type: ignore
__doc__ += "# ContextMenu"
__doc__ += apidoc(solara.lab.components.menu.ContextMenu.f)  # type: ignore

Page = NoPage
