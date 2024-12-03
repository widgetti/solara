"""
# use_router

"""

import solara
from solara.website.components import NoPage
from solara.website.utils import apidoc

title = "use_router"


Page = NoPage


__doc__ += apidoc(solara.use_router)  # type: ignore
