"""
# Select components

Select comes in two flavours:

   * `Select` for a singular selection
   * `SelectMultiple` which allows for multiple selections


"""

import solara
from solara.website.components import NoPage
from solara.website.utils import apidoc

Page = NoPage


__doc__ += "# Select"
__doc__ += apidoc(solara.Select.f)  # type: ignore
__doc__ += "# SelectMultiple"
__doc__ += apidoc(solara.SelectMultiple.f)  # type: ignore
