"""# component_vue

"""
import solara
import solara.autorouting
from solara.website.utils import apidoc

from . import NoPage

title = "component_vue"
Page = NoPage
__doc__ += apidoc(solara.component_vue)  # type: ignore
