"""
# PivotTable

Interactive [Pivot Table](https://en.wikipedia.org/wiki/Pivot_table) showing aggregated data in groups.

We provide three version of the pivot table

    * PivotTableView: Takes already aggregated data as input
    * PivotTable: Takes a dataframe as input and aggregates it for you.
    * PivotTableCard: Similar to PivotTable but with a card layout, and configuration options.

"""

import vaex.datasets

from solara.kitchensink import react, sol

try:
    df = vaex.datasets.titanic()
except Exception:
    df = None


@react.component
def View():
    # select on the 2nd x axis, index=3, which means (pclass=2, survived=true)
    # Note: the indices refer to the header_x and header_y
    selected, on_selected = react.use_state({"x": [1, 3]})
    data = sol.PivotTableData(
        {
            "x": ["pclass", "survived"],
            "y": ["sex"],
            "agg": "count",
            "values": [["5", "118"], ["139", "61"], ["12", "146"], ["94", "25"], ["110", "418"], ["106", "75"]],
            "values_x": ["123", "200", "158", "119", "528", "181"],
            "values_y": ["466", "843"],
            "headers_x": [["1", "1", "2", "2", "3", "3"], ["false", "true", "false", "true", "false", "true"]],
            "headers_y": [["female", "male"]],
            "counts_x": 6,
            "counts_y": 2,
            "total": "1,309",
        }
    )
    with sol.VBox() as main:
        sol.Markdown(f"`selected = {selected}`")
        sol.PivotTableView(data=data, selected=selected, on_selected=on_selected)
    return main


@react.component
def Page():
    with sol.Div() as main:
        sol.Markdown("# Titanic")
        selected, on_selected = react.use_state({"x": [0, 0]})
        sol.provide_cross_filter()
        with sol.VBox():
            type, set_type = react.use_state("view")
            with sol.ToggleButtonsSingle(type, on_value=set_type):
                sol.Button("PivotTableView", value="view")
                sol.Button("PivotTable", value="df")
                sol.Button("PivotTableCard", value="card")
            if type == "view":
                sol.Markdown("# PivotTableView\nThis component will take aggregates data as input")
                View()
            elif type == "df":
                sol.Markdown("# PivotTable\nThis component aggregates the dataframe for you")
                sol.Markdown(f"`selected = {selected}`")
                sol.PivotTable(df, ["pclass"], ["sex"], selected=selected, on_selected=on_selected)
            elif type == "card":
                sol.Markdown("# PivotTable\nThis component aggregates the dataframe for you, and gives a UI to configure the component")
                sol.Markdown(f"`selected = {selected}`")
                sol.PivotTableCard(df, ["pclass"], ["sex"], selected=selected, on_selected=on_selected)
    return main


Component = Page
App = Component
app = Page()
