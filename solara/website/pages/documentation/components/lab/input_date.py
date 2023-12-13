"""
# InputDate

This page contains the two variants of datepickers available in solara

# InputDate
"""
import solara
from solara.website.components import NoPage
from solara.website.utils import apidoc

title = "InputDate"


__doc__ += apidoc(solara.lab.components.input_date.InputDate.f)  # type: ignore
__doc__ += "# InputDateRange"
__doc__ += apidoc(solara.lab.components.input_date.InputDateRange.f)  # type: ignore

Page = NoPage
