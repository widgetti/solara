"""
# computed

"""
import solara
from solara.website.utils import apidoc

from . import NoPage

title = "computed"


Page = NoPage


__doc__ += apidoc(solara.lab.computed)  # type: ignore
