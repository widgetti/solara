"""# FileDownload"""

import solara
from solara.website.components import NoPage
from solara.website.utils import apidoc

Page = NoPage
title = "FileDownload"


__doc__ += apidoc(solara.FileDownload.f)  # type: ignore
