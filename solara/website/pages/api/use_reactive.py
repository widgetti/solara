"""
# use_reactive

"""
import solara
from solara.website.utils import apidoc

from . import NoPage

title = "use_reactive"


Page = NoPage


__doc__ += apidoc(solara.use_reactive)  # type: ignore
