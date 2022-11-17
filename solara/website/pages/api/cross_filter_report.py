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
        solara.lab.CrossFilterReport(df, classes=["py-2"])
        solara.lab.CrossFilterSelect(df, "country")
        solara.lab.CrossFilterSlider(df, "gdpPercap", mode=">")
    return main


__doc__ += apidoc(solara.lab.CrossFilterReport.f)  # type: ignore
