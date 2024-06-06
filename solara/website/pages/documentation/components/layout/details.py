"""
# Details
"""

import solara
from solara.website.components import NoPage
from solara.website.utils import apidoc

title = "Details"

Page = NoPage

__doc__ += apidoc(solara.Details.f)  # type: ignore
