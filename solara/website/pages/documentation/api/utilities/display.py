"""
# display

"""

import solara
from solara.website.components import NoPage
from solara.website.utils import apidoc

title = "display"


Page = NoPage


__doc__ += apidoc(solara.display)  # type: ignore
