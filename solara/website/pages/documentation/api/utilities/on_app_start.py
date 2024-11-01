"""#on_app_start"""

from solara.website.utils import apidoc
import solara.lab
from solara.website.components import NoPage

title = "on_app_start"
Page = NoPage
__doc__ += apidoc(solara.lab.on_app_start)  # type: ignore
