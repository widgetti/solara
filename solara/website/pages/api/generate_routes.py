"""# generate_routes

"""
import solara
import solara.autorouting
from solara.website.utils import apidoc

from . import NoPage

title = "generate_routes"
Page = NoPage
__doc__ += apidoc(solara.autorouting.generate_routes)  # type: ignore
