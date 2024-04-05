"""# Switch"""

import solara
from solara.website.components import NoPage
from solara.website.utils import apidoc

Page = NoPage


__doc__ += apidoc(solara.Switch.f)  # type: ignore
