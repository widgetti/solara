"""
# display

"""
import solara
from solara.website.utils import apidoc

from . import NoPage

title = "display"


Page = NoPage


__doc__ += apidoc(solara.display)  # type: ignore
