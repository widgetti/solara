"""# CrossFilterDataFrame"""

import plotly

import solara
import solara.lab
from solara.website.utils import apidoc

title = "CrossFilterDataFrame"
df = plotly.data.gapminder()


@solara.component
def Page():
    solara.provide_cross_filter()

    solara.CrossFilterReport(df, classes=["py-2"])
    solara.CrossFilterSelect(df, "country")
    solara.CrossFilterDataFrame(df)


__doc__ += apidoc(solara.CrossFilterDataFrame.f)  # type: ignore
