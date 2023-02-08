"""# CrossFilterReport
"""
import plotly

import solara
import solara.lab
from solara.website.utils import apidoc

df = plotly.data.gapminder()


@solara.component
def Page():
    solara.provide_cross_filter()
    with solara.VBox() as main:
        solara.CrossFilterReport(df, classes=["py-2"])
        solara.CrossFilterSelect(df, "country")
        solara.CrossFilterSlider(df, "gdpPercap", mode=">")
    return main


__doc__ += apidoc(solara.CrossFilterReport.f)  # type: ignore
