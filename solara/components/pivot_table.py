import operator
import os
from functools import reduce
from typing import Any, Callable, Dict, List, NoReturn

import ipyvuetify as v

try:
    import numpy as np
except ModuleNotFoundError:
    np = None  # type: ignore
import traitlets

import solara
from solara.alias import rv
from solara.lab.hooks.dataframe import use_df_column_names

cardheight = "100%"


class PivotTableWidget(v.VuetifyTemplate):
    template_file = os.path.realpath(os.path.join(os.path.dirname(__file__), "pivot_table.vue"))
    d = traitlets.Dict(default_value={"no": "data"}).tag(sync=True)
    selected = traitlets.Dict(default_value=[]).tag(sync=True)
    style_ = traitlets.Unicode("").tag(sync=True)


def assert_never(value) -> NoReturn:
    # This also works at runtime as well
    assert False, f"This code should never be reached, got: {value}"


def translate_agg_to_vaex(aggregation: solara.Aggregation, filter=None):
    if aggregation["type"] == "count":
        import vaex

        return vaex.agg.count(selection=filter) if filter else vaex.agg.count()
    assert_never(aggregation)


def df_aggregate_vaex(df, columns: List[str], aggregations: Dict[str, solara.Aggregation], filter=None):
    aggs = {key: translate_agg_to_vaex(agg, filter) for key, agg, in aggregations.items()}
    return df.groupby(columns, sort=True).agg(aggs)


def df_aggregate_pivot_vaex(df, x: List[str], y: List[str], aggregation: solara.Aggregation, filter=None) -> solara.PivotTableData:
    agg_name = aggregation["type"]

    columns = [*x, *y]
    agg_column = "agg_count__"
    row_index = "__row_index__"

    aggregations = {agg_column: aggregation}
    if x and y:
        dfg = df_aggregate_vaex(df, columns, aggregations, filter=filter)
    else:
        dfg = None
    if x:
        dfgx = df_aggregate_vaex(df, x, aggregations, filter=filter)
        dfgx[row_index] = np.arange(len(dfgx), dtype="int64")
    else:
        dfgx = None
    if y:
        dfgy = df_aggregate_vaex(df, y, aggregations, filter=filter)
        dfgy[row_index] = np.arange(len(dfgy), dtype="int64")
    else:
        dfgy = None
    dfg_total = df._agg(translate_agg_to_vaex(aggregations[agg_column], filter=filter))

    def formatter(value):
        if isinstance(value, float):
            return f"{value:,.2f}"
        else:
            return f"{value:,d}"

    if x and y:
        values: List[List[solara.JsonType]] = [[None] * len(dfgy) for _ in range(len(dfgx))]
    else:
        values = [[]]
    if x:
        values_x = list(map(formatter, dfgx[agg_column].tolist()))
        headers_x = [dfgx[k].tolist() for k in x]
        counts_x = len(dfgx)
    else:
        values_x = []
        headers_x = []
        counts_x = 0
    if y:
        values_y = list(map(formatter, dfgy[agg_column].tolist()))
        headers_y = [dfgy[k].tolist() for k in y]
        counts_y = len(dfgy)
    else:
        values_y = []
        headers_y = []
        counts_y = 0
    total = formatter(dfg_total)

    if x and y:
        for row in dfg.to_records():
            dfs = {"x": dfgx, "y": dfgy}
            for column in columns:
                axis_name = "x" if column in x else "y"
                df_axis = dfs[axis_name]
                if row[column] is None:
                    df_axis = df_axis[df[column].ismissing()]
                else:
                    df_axis = df_axis[df_axis[column] == row[column]]
                dfs[axis_name] = df_axis
            assert len(dfs["x"])
            assert len(dfs["y"])
            xi = dfs["x"][row_index].tolist()[0]
            yi = dfs["y"][row_index].tolist()[0]
            value = row[agg_column]
            values[xi][yi] = formatter(value)

    data: solara.PivotTableData = {
        "x": x,
        "y": y,
        "agg": agg_name,
        "values": values,
        "values_x": values_x,
        "values_y": values_y,
        "headers_x": headers_x,
        "headers_y": headers_y,
        "counts_x": counts_x,
        "counts_y": counts_y,
        "total": total,
    }
    return data


def use_df_pivot_data(df, x: List[str], y: List[str], aggregation: solara.Aggregation, filter=None) -> solara.Result[solara.PivotTableData]:
    return solara.use_thread(lambda: df_aggregate_pivot_vaex(df, x, y, aggregation, filter=filter), dependencies=[*x, *y, aggregation, filter])


@solara.component
def PivotTableView(data: solara.PivotTableData, selected: Dict[str, Any] = {}, on_selected: Callable[[Dict[str, Any]], None] = None, style=""):
    return PivotTableWidget.element(d=data, selected=selected, on_selected=on_selected, style_=style)


@solara.component
def PivotTable(
    df,
    x: List[str] = [],
    y: List[str] = [],
    aggregation: solara.Aggregation = solara.AggregationCount(type="count"),
    selected: Dict[str, Any] = {},
    on_selected: Callable[[Dict[str, Any]], None] = None,
):
    x = x.copy()
    y = y.copy()
    filter, set_filter = solara.use_cross_filter(id(df), "pivottable")
    dff = df
    data_result = use_df_pivot_data(dff, x, y, aggregation, filter=filter)
    previous = solara.use_previous(data_result.value, condition=data_result.state == solara.ResultState.FINISHED)
    selected, set_selected = solara.use_state_or_update(selected.copy())

    def set_filter_from_pivot_selection(selection):
        set_selected(selection)
        if on_selected:
            on_selected(selection)
        data = data_result.value
        if data is None:
            return
        # assert data is not None
        filters = []
        if "x" in selection:
            sel = selection["x"]
            for level in range(sel[0] + 1):
                value = data["headers_x"][level][sel[1]]
                column = data["x"][level]
                if value is None:
                    filters.append(df[column].ismissing())
                else:
                    filters.append(df[column] == value)

        if "y" in selection:
            sel = selection["y"]
            for level in range(sel[0] + 1):
                column = data["y"][level]
                value = data["headers_y"][level][sel[1]]
                if value is None:
                    filters.append(df[column].ismissing())
                else:
                    filters.append(df[column] == value)
        if filters:
            filter = reduce(operator.and_, filters[1:], filters[0])
        else:
            filter = None
        set_filter(filter if filter is not None else None)

    # Bug in use_thread on state result we remember that state is finished
    if data_result.state == solara.ResultState.FINISHED and data_result.value is not None:
        with solara.VBox() as main:
            rv.ProgressLinear(indeterminate=False, style_="visibility: hidden;")
            PivotTableView(data=data_result.value, selected=selected, on_selected=set_filter_from_pivot_selection)
    elif previous is not None:
        with solara.VBox() as main:
            rv.ProgressLinear(indeterminate=True)
            PivotTableView(data=previous, selected=selected, on_selected=set_filter_from_pivot_selection, style="opacity: 0.3; pointer-events: none;")
    elif data_result.state == solara.ResultState.ERROR:
        return solara.Error(f"Oops: {data_result.error}")
    else:
        return solara.Info(f"Status: {data_result.state}")
    return main


@solara.component
def PivotTableCard(
    df,
    x=[],
    y=[],
    selected: Dict[str, Any] = {},
    on_selected: Callable[[Dict[str, Any]], None] = None,
):
    items = use_df_column_names(df)
    with rv.Card(elevation=2, style_="position: relative", height=cardheight) as main:
        with rv.CardTitle(children=["Pivot table"]):
            pass
        with rv.CardText():
            with rv.Btn(v_on="x.on", icon=True, absolute=True, style_="right: 10px; top: 10px") as btn:
                rv.Icon(children=["mdi-settings"])
            with rv.Dialog(v_slots=[{"name": "activator", "variable": "x", "children": btn}]):
                with rv.Sheet():
                    with rv.Container(pa_4=True, ma_0=True):
                        with rv.Row():
                            with rv.Col():
                                with rv.Card(elevation=2):
                                    with rv.CardTitle(children=["Rows"]):
                                        pass
                                    with rv.CardText():
                                        for i in range(10):
                                            col = solara.ui_dropdown(value=x[i] if i < len(x) else None, label=f"Row {i}", options=items)
                                            if col is None:
                                                break
                                            else:
                                                if i < len(x):
                                                    x[i] = col
                                                else:
                                                    x.append(col)
                            with rv.Col():
                                with rv.Card(elevation=2):
                                    with rv.CardTitle(children=["Columns"]):
                                        pass
                                    with rv.CardText():
                                        for i in range(10):
                                            col = solara.ui_dropdown(value=y[i] if i < len(y) else None, label=f"Column {i}", options=items)
                                            if col is None:
                                                break
                                            else:
                                                if i < len(y):
                                                    y[i] = col
                                                else:
                                                    y.append(col)

            PivotTable(df, x, y, selected=selected, on_selected=on_selected)

    return main
