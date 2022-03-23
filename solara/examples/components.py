from solara.kitchensink import react, v
import solara as sol
import solara.components.datatable

import vaex

df = vaex.datasets.titanic()
# import ipyvue

# ipyvue.watch()

import solara.widgets

solara.widgets.watch()


@react.component
def DataTableDemo():
    return sol.components.datatable.DataTable(df)


tabs = {
    "DataTable": DataTableDemo,
}


@react.component
def Components():
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


app = Components()
