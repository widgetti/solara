"""# Tooltip"""

import solara
from solara.website.components import NoPage
from solara.website.utils import apidoc

Page = NoPage
title = "Tooltip"


__doc__ += apidoc(solara.Tooltip.f)  # type: ignore
