"""# Text"""

import solara
from solara.website.components import NoPage
from solara.website.utils import apidoc

Page = NoPage
title = "Text"


__doc__ += apidoc(solara.Text.f)  # type: ignore
