"""# Input fields

This page contains all the input fields available in Solara.

# InputText
"""
import solara
from solara.website.utils import apidoc

from . import NoPage

Page = NoPage


__doc__ += apidoc(solara.InputText.f)  # type: ignore
__doc__ += "# InputFloat"
__doc__ += apidoc(solara.InputFloat.f)  # type: ignore
__doc__ += "# InputInt"
__doc__ += apidoc(solara.InputInt.f)  # type: ignore
