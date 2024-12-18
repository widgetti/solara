"""
# InputTime
"""

import solara
from solara.website.components import NoPage
from solara.website.utils import apidoc

title = "InputTime"


__doc__ += apidoc(solara.lab.components.input_time.InputTime.f)  # type: ignore


Page = NoPage
