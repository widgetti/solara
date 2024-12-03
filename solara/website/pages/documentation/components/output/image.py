"""# Image"""

import solara
from solara.website.components import NoPage
from solara.website.utils import apidoc

Page = NoPage
title = "Image"


__doc__ += apidoc(solara.Image.f)  # type: ignore
