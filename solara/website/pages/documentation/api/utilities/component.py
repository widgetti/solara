"""# component"""

import solara
from solara.website.components import NoPage
from solara.website.utils import apidoc

Page = NoPage
title = "component"


__doc__ += apidoc(solara.component)  # type: ignore
