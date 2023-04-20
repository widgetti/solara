"""
# Spinner
"""
import solara
from solara.website.utils import apidoc

from . import NoPage

Page = NoPage

__doc__ += "# SpinnerSolara"
__doc__ += apidoc(solara.SpinnerSolara.f)  # type: ignore
