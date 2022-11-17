"""# CrossFilterSelect
"""
import plotly

import solara
import solara.lab
from solara.website.utils import apidoc

df = plotly.data.tips()


@solara.component
def Page():
    solara.provide_cross_filter()
    with solara.VBox() as main:
        solara.lab.CrossFilterReport(df, classes=["py-2"])
        solara.lab.CrossFilterSelect(df, "sex")
        solara.lab.CrossFilterSelect(df, "time")
    return main


__doc__ += apidoc(solara.lab.CrossFilterSelect.f)  # type: ignore
