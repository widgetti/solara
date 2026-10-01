"""# component_html"""

import solara
import solara.autorouting
from solara.website.components import NoPage
from solara.website.utils import apidoc

title = "component_html"
Page = NoPage
__doc__ += apidoc(solara.component_html)  # type: ignore
