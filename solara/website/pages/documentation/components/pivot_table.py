"""
# PivotTable

Interactive [Pivot Table](https://en.wikipedia.org/wiki/Pivot_table) showing aggregated data in groups.

We provide three version of the pivot table

    * PivotTableView: Takes already aggregated data as input
    * PivotTable: Takes a dataframe as input and aggregates it for you.
    * PivotTableCard: Similar to PivotTable but with a card layout, and configuration options.

"""

import solara

try:
    import vaex.datasets

    df = vaex.datasets.titanic()
except Exception:
    df = None
    vaex = None


@solara.component
def View():
    # select on the 2nd x axis, index=3, which means (pclass=2, survived=true)
    # Note: the indices refer to the header_x and header_y
    selected, on_selected = solara.use_state({"x": [1, 3]})
    data = solara.PivotTableData(
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
    with solara.VBox() as main:
        solara.Markdown(f"`selected = {selected}`")
        solara.PivotTableView(data=data, selected=selected, on_selected=on_selected)
    return main


@solara.component
def Page():
    if vaex is None:
        return solara.Markdown("This example requires vaex, please install it with `pip install vaex`")
    with solara.Div() as main:
        solara.Markdown("# Titanic")
        selected, on_selected = solara.use_state({"x": [0, 0]})
        solara.provide_cross_filter()
        with solara.VBox():
            type, set_type = solara.use_state("view")
            with solara.ToggleButtonsSingle(type, on_value=set_type):
                solara.Button("PivotTableView", value="view")
                solara.Button("PivotTable", value="df")
                solara.Button("PivotTableCard", value="card")
            if type == "view":
                solara.Markdown("# PivotTableView\nThis component will take aggregates data as input")
                View()
            elif type == "df":
                solara.Markdown("# PivotTable\nThis component aggregates the dataframe for you")
                solara.Markdown(f"`selected = {selected}`")
                solara.PivotTable(df, ["pclass"], ["sex"], selected=selected, on_selected=on_selected)
            elif type == "card":
                solara.Markdown("# PivotTable\nThis component aggregates the dataframe for you, and gives a UI to configure the component")
                solara.Markdown(f"`selected = {selected}`")
                solara.PivotTableCard(df, ["pclass"], ["sex"], selected=selected, on_selected=on_selected)
    return main


Component = Page
App = Component
app = Page()
