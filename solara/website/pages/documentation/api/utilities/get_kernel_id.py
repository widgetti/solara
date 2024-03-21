"""
# get_kernel_id

"""

import solara
from solara.website.components import NoPage
from solara.website.utils import apidoc

title = "get_kernel_id"


Page = NoPage


__doc__ += apidoc(solara.get_kernel_id)  # type: ignore
