"""
# computed

"""

import solara
from solara.website.components import NoPage
from solara.website.utils import apidoc

title = "computed"


Page = NoPage


__doc__ += apidoc(solara.lab.computed)  # type: ignore
