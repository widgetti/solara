"""
# use_reactive

"""

import solara
from solara.website.components import NoPage
from solara.website.utils import apidoc

title = "use_reactive"


Page = NoPage


__doc__ += apidoc(solara.use_reactive)  # type: ignore
