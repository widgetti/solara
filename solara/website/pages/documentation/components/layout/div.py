"""# Div"""

import solara
from solara.website.components import NoPage
from solara.website.utils import apidoc

Page = NoPage
title = "Div"


__doc__ += apidoc(solara.Div.f)  # type: ignore
