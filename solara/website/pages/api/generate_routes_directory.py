"""# generate_routes_directory

"""
import solara
import solara.autorouting
from solara.website.utils import apidoc

from . import NoPage

title = "generate_routes_directory"
Page = NoPage
__doc__ += apidoc(solara.autorouting.generate_routes_directory)  # type: ignore
