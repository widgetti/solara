from solara.kitchensink import react, v

from .calculator import Calculator
from .pokemon import App as Pokemon

tabs = {
    "Calulator": Calculator,
    "Pokemon": Pokemon,
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
            component()
    return main
