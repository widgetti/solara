from solara.kitchensink import react, v

from .calculator import Calculator
from .bqplot import Plot
from .plotly import Plotly
from .altair import Altair


tabs = {
    "Calulator": Calculator,
    "Bqplot": Plot,
    "Plotly": Plotly,
    "Altair": Altair,
}


@react.component
def Demo():
    tab, set_tab = react.use_state(0, "tab")

    # md, set_md = use_state("")
    with v.Tabs(v_model=tab, on_v_model=set_tab, vertical=True) as main:
        for key in tabs:
            with v.Tab(children=[key]):
                pass
        component = list(tabs.values())[tab]
        with v.TabsItems(v_model=tab):
            component(__key__=tab)
    return main
