"""
# Sliders

To support proper typechecks, we have multiple slider (all wrapping the ipyvuetify sliders).


"""
import solara
from solara.website.utils import apidoc

from . import NoPage

Page = NoPage

__doc__ += "# SliderInt"
__doc__ += apidoc(solara.SliderInt.f)  # type: ignore
__doc__ += "# SliderRangeInt"
__doc__ += apidoc(solara.SliderRangeInt.f)  # type: ignore

__doc__ += "# SliderFloat"
__doc__ += apidoc(solara.SliderFloat.f)  # type: ignore
__doc__ += "# SliderRangeFloat"
__doc__ += apidoc(solara.SliderRangeFloat.f)  # type: ignore

__doc__ += "# SliderValue"
__doc__ += apidoc(solara.SliderValue.f)  # type: ignore

__doc__ += "# SliderDate"
__doc__ += apidoc(solara.SliderDate.f)  # type: ignore
