from typing import cast

from solara.kitchensink import react, v

from .altair import Altair
from .bqplot import Plot
from .plotly import Plotly

tabs = {
    "Bqplot": Plot,
    "Plotly": Plotly,
    "Altair": Altair,
}


@react.component
def Libraries():
    tab, set_tab = react.use_state(0, "tab")

    # md, set_md = use_state("")
    with v.Tabs(v_model=tab, on_v_model=set_tab, vertical=True) as main:
        for key in tabs:
            with v.Tab(children=[key]):
                pass
        component = cast(react.core.Component, list(tabs.values())[tab])
        with v.TabsItems(v_model=tab):
            component().key(str(tab))
    return main


app = Libraries()
