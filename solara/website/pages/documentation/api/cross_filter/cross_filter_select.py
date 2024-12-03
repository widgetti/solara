"""# CrossFilterSelect"""

import plotly

import solara
import solara.lab
from solara.website.utils import apidoc

df = plotly.data.tips()


@solara.component
def Page():
    solara.provide_cross_filter()
    solara.CrossFilterReport(df, classes=["py-2"])
    solara.CrossFilterSelect(df, "sex")
    solara.CrossFilterSelect(df, "time")


__doc__ += apidoc(solara.CrossFilterSelect.f)  # type: ignore
