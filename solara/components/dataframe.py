import operator
from functools import reduce
from typing import List, cast

import numpy as np
import react_ipywidgets as react
import react_ipywidgets.bqplot as bqplot
import react_ipywidgets.ipyvuetify as v
import react_ipywidgets.ipywidgets as w

from solara.components import PivotTable, ui_checkbox, ui_dropdown
from solara.hooks import df_unique, max_unique, use_cross_filter, use_df_column_names
from solara.hooks.dataframe import use_df_pivot_data

cardheight = "100%"


@react.component
def ExpressionEditor(df, value: str, label="Custom expression", on_value=None, placeholder="Enter an expression", prepend_icon="function"):
    """Editor for expression for Vaex, on_value will only be triggered for valid expressions"""

    def get_error(value):
        if value is None:
            return None
        try:
            df.validate_expression(value)
            return None
        except Exception as e:
            return str(e)

    value, set_value = react.use_state(value)
    error: List = []
    error, set_error = react.use_state(cast(List, []))
    set_error([get_error(value)])

    def on_value_local(value):
        error = get_error(value)
        set_value(value)
        set_error([error])

        if not error and on_value:
            on_value(df[value])

    return v.TextField(
        label=label,
        v_model=value,
        on_v_model=on_value_local,
        placeholder=placeholder,
        prepend_icon="mdi-filter",
        error_messages=error,
        success_messages="Looking good" if value is not None else None,
    )


@react.component
def FilterCard(df):
    filter, set_filter = use_cross_filter("filter-custom")

    with v.Card(elevation=2, height=cardheight) as main:
        with v.CardTitle(children=["Filter"]):
            pass
        with v.CardText():
            ExpressionEditor(df, "", on_value=set_filter)
    return main


@react.component
def Table(df, n=5):
    output_c = w.Output()

    def output():
        import ipywidgets as widgets

        output_real: widgets.Output = react.get_widget(output_c)
        # don't rely on display, does not work in solara yet
        with output_real.hold_sync():
            output_real.outputs = tuple()
            output_real.append_display_data(df)

    react.use_side_effect(output)
    return output_c


@react.component
def TableCard(df):
    filter, set_filter = use_cross_filter(None)
    dff = df
    filtered = False
    if filter is not None:
        filtered = True
        dff = df[filter]
    if filtered:
        title = "Filtered"
    else:
        title = "Showing all"
    title = "Showing first 10 rows"
    progress = len(dff) / len(df) * 100
    with v.Card(elevation=2, height=cardheight) as main:
        with v.CardTitle(children=[title]):
            if filtered:
                v.ProgressLinear(value=progress)
        with v.CardText():
            Table(dff)
    return main


@react.component
def HistogramCard(df, column=None):
    filter, set_filter = use_cross_filter("filter-histogram")
    dff = df  # filter(df)

    items = df.get_column_names()

    with v.Card(elevation=2, height=cardheight) as main:
        with v.CardTitle(children=["Histogram"]):
            pass
        with v.CardText():
            with v.Btn(v_on="x.on", icon=True, absolute=True, style_="right: 10px; top: 10px") as btn:
                v.Icon(children=["mdi-settings"])
            with v.Dialog(v_slots=[{"name": "activator", "variable": "x", "children": btn}], width="500"):
                with v.Sheet():
                    with v.Card(elevation=2):
                        with v.CardTitle(children=["Histgram input"]):
                            pass
                        with v.CardText():
                            column = items[0] if column not in items else column
                            column = ui_dropdown(value=column, description="x", options=items)
            if column:
                log = False
                import vaex

                dfg = dff.groupby(column, agg={"count": vaex.agg.count(selection=filter)}, sort=True)
                if len(dfg) > max_unique:
                    with v.Alert(
                        type="warning",
                        text=True,
                        prominent=True,
                        icon="mdi-alert",
                        children=[f"Too many unique values: {len(dfg)}, only showing first {max_unique}"],
                    ):
                        pass
                    dfg = dfg[:max_unique]
                if 1:
                    x = dfg[column].to_numpy()
                    y = dfg["count"].to_numpy()
                    if df[column].dtype == bool:
                        scale_x = bqplot.OrdinalScale()
                        x = np.where(x.astype("int8"), "true", "false")
                    elif dfg[column].dtype == str:
                        scale_x = bqplot.OrdinalScale()
                    else:
                        scale_x = bqplot.OrdinalScale()
                    if log:
                        scale_y = bqplot.LogScale()
                    else:
                        scale_y = bqplot.LinearScale()

                    def on_selected(selected):
                        print("selected", selected)
                        if selected is not None:
                            if df[column].dtype == bool:
                                value = [True, False][selected[0]]
                            else:
                                value = x[selected[0]]
                            expression = df[column] == value
                            set_filter(expression)
                        else:
                            set_filter(None)

                    lines = bqplot.Bars(
                        x=x.tolist(),
                        y=y.tolist(),
                        scales={"x": scale_x, "y": scale_y},
                        type="grouped",
                        selected_style={"fill": "#f55"},
                        on_selected=on_selected,
                        interactions={"click": "select"},
                    )
                    x_axis = bqplot.Axis(scale=scale_x, label=column)
                    y_axis = bqplot.Axis(scale=scale_y, orientation="vertical", label="count")
                    axes = [x_axis, y_axis]
                    bqplot.Figure(axes=axes, marks=[lines])
    return main


@react.component
def ScatterCard(df, x=None, y=None, color=None):
    filter, set_filter = use_cross_filter("filter-scatter")
    dff = df
    if filter:
        dff = df[filter]
    columns = df.get_column_names()
    max_points = 1000
    floats = [k for k in columns if df[k].dtype == float]
    #     flots = df.get_column_names()

    with v.Card(elevation=2, height=cardheight) as main:
        with v.CardTitle(children=["Scatter"]):
            pass
        with v.CardText():
            with v.Btn(v_on="x.on", icon=True, absolute=True, style_="right: 10px; top: 10px") as btn:
                v.Icon(children=["mdi-settings"])
            with v.Dialog(v_slots=[{"name": "activator", "variable": "x", "children": btn}], width="500"):
                with v.Sheet():
                    with v.Card(elevation=2):
                        with v.CardTitle(children=["Histgram input"]):
                            pass
                        with v.CardText():
                            xcol = x
                            if xcol is None:
                                xcol = xcol if len(floats) == 0 else floats[0]
                            xcol = ui_dropdown(value=xcol, description="x", options=floats)
                            ycol = y
                            if ycol is None:
                                ycol = ycol if len(floats) < 2 else floats[1]
                            ycol = ui_dropdown(value=ycol, description="y", options=floats)
                            ccol = color
                            if ccol is None:
                                ccol = ccol if len(floats) < 3 else floats[0]
                            ccol = ui_dropdown(value=ccol, description="Color", options=floats)
            if xcol and ycol:
                if len(dff) > max_points:
                    v.Alert(
                        type="warning", text=True, prominent=True, icon="mdi-alert", children=[f"Too many unique values, will only show first {max_points}"]
                    )
                    dff = dff[:max_points]

                x = dff[xcol].to_numpy()
                y = dff[ycol].to_numpy()
                if ccol is not None:
                    colord = dff[ccol].to_numpy().tolist()
                else:
                    colord = None

                if df[xcol].dtype == bool:
                    scale_x = bqplot.OrdinalScale()
                    x = np.where(x.astype("int8"), "true", "false")
                elif df[xcol].dtype == str:
                    scale_x = bqplot.OrdinalScale()
                else:
                    scale_x = bqplot.LinearScale()

                if df[ycol].dtype == bool:
                    scale_y = bqplot.OrdinalScale()
                    y = np.where(y.astype("int8"), "true", "false")
                elif df[ycol].dtype == str:
                    scale_y = bqplot.OrdinalScale()
                else:
                    scale_y = bqplot.LinearScale()

                def on_selected(selected):
                    if selected is not None and len(selected) > 0:
                        if df[xcol].dtype == bool:
                            value_x = [True, False][selected[0]]
                        else:
                            value_x = x[selected[0]]
                        if df[ycol].dtype == bool:
                            value_y = [True, False][selected[0]]
                        else:
                            value_y = y[selected[0]]
                        expression = (df[xcol] == value_x) & (df[ycol] == value_y)
                        set_filter(expression)
                    else:
                        set_filter(None)

                scale_color = bqplot.ColorScale()
                scatter = bqplot.Scatter(
                    x=x,
                    y=y,
                    scales={"x": scale_x, "y": scale_y, "color": scale_color},
                    color=colord,
                    selected_style={"fill": "#f55"},
                    on_selected=on_selected,
                    interactions={"click": "select"},
                )
                x_axis = bqplot.Axis(scale=scale_x, label=xcol)
                y_axis = bqplot.Axis(scale=scale_y, orientation="vertical", label=ycol)
                axes = [x_axis, y_axis]
                marks = [scatter]
                bqplot.Figure(axes=axes, marks=marks)
    return main


color_maps = [
    "Spectral",
    "RdYlGn",
    "RdBu",
    "PiYG",
    "PRGn",
    "RdYlBu",
    "BrBG",
    "RdGy",
    "PuOr",
    "Set2",
    "Accent",
    "Set1",
    "Set3",
    "Dark2",
    "Paired",
    "Pastel2",
    "Pastel1",
    "OrRd",
    "PuBu",
    "BuPu",
    "Oranges",
    "BuGn",
    "YlOrBr",
    "YlGn",
    "Reds",
    "RdPu",
    "Greens",
    "YlGnBu",
    "Purples",
    "GnBu",
    "Greys",
    "YlOrRd",
    "PuRd",
    "Blues",
    "PuBuGn",
    "viridis",
    "plasma",
    "inferno",
    "magma",
]

cardheight = "100%"


@react.component
def HeatmapCard(df, x=None, y=None, debounce=True):
    limit_keys = "xmin xmax ymin ymax".split()
    limits, set_limits = react.use_state(dict.fromkeys(limit_keys))
    contrast, set_contrast = react.use_state([0.5, 99.5])
    # print("limits", limits)
    limits = limits.copy()
    filter, set_filter = use_cross_filter("filter-heatmap")
    dff = df
    selection = filter
    # print("unfiltered", dff is df)

    items = df.get_column_names()
    floats = [k for k in items if df[k].dtype == float]

    with v.Card(elevation=2, height=cardheight) as main:
        with v.CardTitle(children=["Heatmap"]):
            pass
        with v.CardText():
            with v.Btn(v_on="x.on", icon=True, absolute=True, style_="right: 10px; top: 10px") as btn:
                v.Icon(children=["mdi-settings"])
            with v.Dialog(v_slots=[{"name": "activator", "variable": "x", "children": btn}], width="700"):
                with v.Sheet():
                    with v.Card(elevation=2):
                        with v.CardTitle(children=["Histgram input"]):
                            pass
                        with v.CardText():
                            xcol = x
                            if xcol is None:
                                xcol = xcol if len(floats) == 0 else floats[0]
                            xcol = ui_dropdown(value=xcol, description="x", options=floats)
                            ycol = y
                            if ycol is None:
                                ycol = ycol if len(floats) == 0 else floats[1]
                            ycol = ui_dropdown(value=ycol, description="y", options=floats)
                            scheme = ui_dropdown(value=color_maps[0], options=color_maps)
                            v.RangeSlider(v_model=contrast, on_v_model=set_contrast, label="Contrast", min=0, max=100)
                            crossfilter_visible = ui_checkbox(value=False, description="Cross filter visible")

            if xcol and ycol:
                import vaex.jupyter

                def updater(name):
                    @react.use_memo
                    def make(name):
                        # def shared():  # all render functions get a shared function per 'name'
                        def setter(value):
                            def state_updater(state):
                                return {**state, name: value}

                            set_limits(state_updater)

                        if debounce:
                            return vaex.jupyter.debounced(0.3)(setter)
                        else:
                            return setter
                        # return shared

                    return make(name)

                update_xmin = updater("xmin")
                update_xmax = updater("xmax")
                update_ymin = updater("ymin")
                update_ymax = updater("ymax")

                print("limits", limits)

                # def update(name):
                #     def update_single(value):
                #         update_single_debouced(name, value)
                #     return update_single

                @react.use_memo
                def minx(x):
                    values = [k.item() for k in dff[x].minmax()]
                    update_xmin(values[0])
                    update_xmax(values[1])

                minx(xcol)

                @react.use_memo
                def miny(y):
                    values = [k.item() for k in dff[y].minmax()]
                    update_ymin(values[0])
                    update_ymax(values[1])

                miny(ycol)

                if all(limits[k] is not None for k in limit_keys):
                    # print("limits used", limits)
                    xrange = limits["xmin"], limits["xmax"]
                    yrange = limits["ymin"], limits["ymax"]

                    @react.use_memo
                    def cross_filter(crossfilter_visible, xrange, yrange):
                        if crossfilter_visible:
                            visible_filter = (df[xcol] >= xrange[0]) & (df[xcol] <= xrange[1]) & (df[ycol] >= yrange[0]) & (df[ycol] <= yrange[1])
                            set_filter(visible_filter)
                        else:
                            set_filter(None)

                    cross_filter(crossfilter_visible, xrange, yrange)

                    # @react.use_memo

                    def grid(xcol, ycol, limits):
                        vaex_limits = [xrange, yrange]
                        # print(xcol, ycol, vaex_limits)
                        # print("grid", len(dff))
                        return dff.count(binby=(xcol, ycol), limits=vaex_limits, shape=(512, 256), selection=selection)

                    values = grid(xcol, ycol, limits).astype("float32").T

                    vmin = np.percentile(values.ravel(), contrast[0]).item()
                    vmax = np.percentile(values.ravel(), contrast[1]).item()
                    if vmin == vmax:
                        vmax = values.min().item()
                        vmax = values.max().item()
                    # print(values.min(), values.max(), vmin, vmax, contrast)

                    scale_x = bqplot.LinearScale(allow_padding=False, on_min=update_xmin, on_max=update_xmax)  # min=0, max=1)
                    scale_y = bqplot.LinearScale(allow_padding=False, on_min=update_ymin, on_max=update_ymax)  # min=0, max=1)
                    scales = {"x": scale_x, "y": scale_y, "image": bqplot.ColorScale(min=vmin, max=vmax, scheme=scheme)}
                    from bqplot_image_gl import ImageGL

                    image = ImageGL.element(image=values, scales=scales, x=xrange, y=yrange)
                    panzoom = bqplot.PanZoom(scales={"x": [scales["x"]], "y": [scales["y"]]})

                    x_axis = bqplot.Axis(scale=scale_x, label=xcol)
                    y_axis = bqplot.Axis(scale=scale_y, orientation="vertical", label=ycol)
                    axes = [x_axis, y_axis]
                    marks = [image]
                    bqplot.Figure(axes=axes, marks=marks, interaction=panzoom)
    return main


@react.component
def SummaryCard(df):
    filter, set_filter = use_cross_filter(None)
    dff = df
    filtered = False
    if filter is not None:
        filtered = True
        dff = df[filter]
    if filtered:
        title = "Filtered"
    else:
        title = "Showing all"
    progress = len(dff) / len(df) * 100
    with v.Card(elevation=2, height=cardheight) as main:
        with v.CardTitle(children=[title]):
            if filtered:
                v.ProgressLinear(value=progress)
        with v.CardText():
            icon = "mdi-filter"
            v.Icon(children=[icon], style_="opacity: 0.1" if not filtered else "")
            if filtered:
                summary = f"{len(dff):,} / {len(df):,}"
            else:
                summary = f"{len(dff):,}"
            v.Html(tag="h3", children=[summary], style_="display: inline")
    return main


@react.component
def DropdownCard(df, column=None):
    max_unique = 100
    filter, set_filter = use_cross_filter("filter-dropdown")
    columns = use_df_column_names(df)
    column, set_column = react.use_state(columns[0] if column is None else column)
    uniques = df_unique(df, column, limit=max_unique + 1)
    value, set_value = react.use_state(None)
    # to avoid confusing vuetify about selecting 'None' and nothing
    magic_value_missing = "__missing_value__"

    def set_value_and_filter(value):
        set_value(value)
        # print(value)
        if value is None:
            set_filter(None)
        else:
            value = value["value"]
            if value == magic_value_missing:
                set_filter(str(df[column].ismissing()))
            else:
                filter = df[column] == value
                # print(filter)
                set_filter(filter)

    with v.Card(elevation=2, height=cardheight) as main:
        with v.CardTitle(children=["Filter out single value"]):
            pass
        with v.CardText():
            with v.Btn(v_on="x.on", icon=True, absolute=True, style_="right: 10px; top: 10px") as btn:
                v.Icon(children=["mdi-settings"])
            with v.Dialog(v_slots=[{"name": "activator", "variable": "x", "children": btn}], width="500"):
                with v.Sheet():
                    with v.Container(pa_4=True, ma_0=True):
                        with v.Row():
                            with v.Col():
                                v.Select(v_model=column, items=columns, on_v_model=set_column, label="Choose column")
            # we use objects to we can distinguish between selecting nothing or None
            items = [{"value": magic_value_missing if k is None else k, "text": str(k)} for k in uniques]
            v.Select(v_model=value, items=items, on_v_model=set_value_and_filter, label=f"Choose {column} value", clearable=True, return_object=True)
            if len(uniques) > max_unique:
                v.Alert(type="warning", text=True, prominent=True, icon="mdi-alert", children=[f"Too many unique values, will only show first {max_unique}"])

    return main


@react.component
def PivotTableCard(df, x=[], y=[]):
    # copy since we mutate
    x = x.copy()
    y = y.copy()
    filter, set_filter = use_cross_filter("pivottable")
    dff = df

    def set_filter_from_pivot_selection(selection):
        assert data is not None
        filters = []
        # print("selection", selection)
        if "x" in selection:
            sel = selection["x"]
            for level in range(sel[0] + 1):
                value = data["headers"]["x"][level][sel[1]]
                column = data["x"][level]
                if value is None:
                    filters.append(df[column].ismissing())
                else:
                    filters.append(df[column] == value)

        if "y" in selection:
            sel = selection["y"]
            for level in range(sel[0] + 1):
                column = data["y"][level]
                value = data["headers"]["y"][level][sel[1]]
                if value is None:
                    filters.append(df[column].ismissing())
                else:
                    filters.append(df[column] == value)
        #         if filters:
        #             expression = "&".join([k.expression for k in filters])
        #         else:
        #             expression = None
        if filters:
            #             otherfilters_expressions = [df[k] for k in otherfilters]
            filter = reduce(operator.and_, filters[1:], filters[0])
        #             return df[filter]
        else:
            filter = None
        # print(filter)
        set_filter(filter)

    data = None
    items = use_df_column_names(df)
    with v.Card(elevation=2, style_="position: relative", height=cardheight) as main:
        with v.CardTitle(children=["Pivot table"]):
            pass
        with v.CardText():
            with v.Btn(v_on="x.on", icon=True, absolute=True, style_="right: 10px; top: 10px") as btn:
                v.Icon(children=["mdi-settings"])
            with v.Dialog(v_slots=[{"name": "activator", "variable": "x", "children": btn}]):
                with v.Sheet():
                    with v.Container(pa_4=True, ma_0=True):
                        with v.Row():
                            with v.Col():
                                with v.Card(elevation=2):
                                    with v.CardTitle(children=["Rows"]):
                                        pass
                                    with v.CardText():
                                        for i in range(10):
                                            col = ui_dropdown(value=x[i] if i < len(x) else None, description=f"Row {i}", options=items)
                                            if col is None:
                                                break
                                            else:
                                                if i < len(x):
                                                    x[i] = col
                                                else:
                                                    x.append(col)
                            with v.Col():
                                with v.Card(elevation=2):
                                    with v.CardTitle(children=["Columns"]):
                                        pass
                                    with v.CardText():
                                        for i in range(10):
                                            col = ui_dropdown(value=y[i] if i < len(y) else None, description=f"Column {i}", options=items)
                                            if col is None:
                                                break
                                            else:
                                                if i < len(y):
                                                    y[i] = col
                                                else:
                                                    y.append(col)

            import vaex

            data = use_df_pivot_data(dff, x, y, vaex.agg.count(selection=filter))
            PivotTable(d=data, on_selected=set_filter_from_pivot_selection)

    return main
