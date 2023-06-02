from typing import List, cast

import numpy as np
import reacton.bqplot as bqplot
import reacton.ipyvuetify as v
import reacton.ipywidgets as w

import solara
from solara.components import ui_checkbox, ui_dropdown
from solara.hooks import use_cross_filter
from solara.lab.hooks.dataframe import use_df_column_names
from solara.lab.utils.dataframe import df_unique

cardheight = "100%"


@solara.component
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

    value, set_value = solara.use_state(value)
    error: List = []
    error, set_error = solara.use_state(cast(List, []))
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


@solara.component
def FilterCard(df):
    filter, set_filter = use_cross_filter(id(df), "filter-custom")

    with v.Card(elevation=2, height=cardheight) as main:
        with v.CardTitle(children=["Filter"]):
            pass
        with v.CardText():
            ExpressionEditor(df, "", on_value=set_filter)
    return main


@solara.component
def Table(df, n=5):
    output_c = w.Output()

    def output():
        import ipywidgets as widgets

        output_real: widgets.Output = solara.get_widget(output_c)
        # don't rely on display, does not work in solara yet
        with output_real.hold_sync():
            output_real.outputs = tuple()
            output_real.append_display_data(df)

    solara.use_side_effect(output)
    return output_c


@solara.component
def TableCard(df):
    filter, set_filter = use_cross_filter(id(df), "table")
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


@solara.component
def HistogramCard(df, column=None, max_unique=100):
    filter, set_filter = use_cross_filter(id(df), "filter-histogram")
    dff = df  # filter(df)

    items = use_df_column_names(df)

    with v.Card(elevation=2, height=cardheight) as main:
        with v.CardTitle(children=["Histogram"]):
            pass
        with v.CardText():
            with v.Btn(v_on="x.on", icon=True, absolute=True, style_="right: 10px; top: 10px") as btn:
                v.Icon(children=["mdi-settings"])
            with v.Dialog(v_slots=[{"name": "activator", "variable": "x", "children": btn}], width="500"):
                with v.Sheet():
                    with v.Card(elevation=2):
                        with v.CardTitle(children=["Histogram input"]):
                            pass
                        with v.CardText():
                            column = items[0] if column not in items else column
                            column = ui_dropdown(value=column, label="x", options=items)
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
                        scale_x = bqplot.OrdinalScale(domain=x.tolist())
                    else:
                        scale_x = bqplot.OrdinalScale()
                    if log:
                        scale_y = bqplot.LogScale()
                    else:
                        scale_y = bqplot.LinearScale()

                    def on_selected(selected):
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
                        colors=["rgba(58, 130, 246, 0.5)"],
                        x=x.tolist(),
                        y=y.tolist(),
                        scales={"x": scale_x, "y": scale_y},
                        type="grouped",
                        selected_style={"fill": "rgba(58, 130, 246, 0.8)"},
                        on_selected=on_selected,
                        interactions={"click": "select"},
                    )
                    x_axis = bqplot.Axis(
                        scale=scale_x,
                        label=column,
                        grid_lines="none",
                        color="rgba(0,0,0,0)",
                        tick_style={
                            "fill": "rgba(0,0,0,0.8)",
                        },
                    )
                    y_axis = bqplot.Axis(
                        scale=scale_y,
                        orientation="vertical",
                        label="count",
                        color="rgba(0,0,0,0)",
                        tick_style={
                            "fill": "rgba(0,0,0,0.8)",
                        },
                    )
                    axes = [x_axis, y_axis]
                    bqplot.Figure(axes=axes, marks=[lines])
    return main


@solara.component
def ScatterCard(df, x=None, y=None, color=None):
    filter, set_filter = use_cross_filter(id(df), "filter-scatter")
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
                        with v.CardTitle(children=["Histogram input"]):
                            pass
                        with v.CardText():
                            xcol = x
                            if xcol is None:
                                xcol = xcol if len(floats) == 0 else floats[0]
                            xcol = ui_dropdown(value=xcol, label="x", options=floats)
                            ycol = y
                            if ycol is None:
                                ycol = ycol if len(floats) < 2 else floats[1]
                            ycol = ui_dropdown(value=ycol, label="y", options=floats)
                            ccol = color
                            if ccol is None:
                                ccol = ccol if len(floats) < 3 else floats[0]
                            ccol = ui_dropdown(value=ccol, label="Color", options=floats)
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


@solara.component
def HeatmapCard(df, x=None, y=None, debounce=True):
    limit_keys = "xmin xmax ymin ymax".split()
    limits, set_limits = solara.use_state(dict.fromkeys(limit_keys))
    contrast, set_contrast = solara.use_state([0.5, 99.5])
    # print("limits", limits)
    limits = limits.copy()
    filter, set_filter = use_cross_filter(id(df), "filter-heatmap")
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
                        with v.CardTitle(children=["Histogram input"]):
                            pass
                        with v.CardText():
                            xcol = x
                            if xcol is None:
                                xcol = xcol if len(floats) == 0 else floats[0]
                            xcol = ui_dropdown(value=xcol, label="x", options=floats)
                            ycol = y
                            if ycol is None:
                                ycol = ycol if len(floats) == 0 else floats[1]
                            ycol = ui_dropdown(value=ycol, label="y", options=floats)
                            scheme = ui_dropdown("Color map", value=color_maps[0], options=color_maps)
                            v.RangeSlider(v_model=contrast, on_v_model=set_contrast, label="Contrast", min=0, max=100)
                            crossfilter_visible = ui_checkbox(value=False, label="Cross filter visible")

            if xcol and ycol:
                import vaex.jupyter

                def updater(name):
                    def make():
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

                    return solara.use_memo(make, [name])

                update_xmin = updater("xmin")
                update_xmax = updater("xmax")
                update_ymin = updater("ymin")
                update_ymax = updater("ymax")

                # def update(name):
                #     def update_single(value):
                #         update_single_debouced(name, value)
                #     return update_single

                def minx(x):
                    values = [k.item() for k in dff[x].minmax()]
                    update_xmin(values[0])
                    update_xmax(values[1])

                solara.use_memo(lambda: minx(xcol), [xcol])

                # @solara.use_memo
                def miny(y):
                    values = [k.item() for k in dff[y].minmax()]
                    update_ymin(values[0])
                    update_ymax(values[1])

                solara.use_memo(lambda: miny(ycol), [ycol])

                if all(limits[k] is not None for k in limit_keys):
                    # print("limits used", limits)
                    xrange = limits["xmin"], limits["xmax"]
                    yrange = limits["ymin"], limits["ymax"]

                    def cross_filter():
                        if crossfilter_visible:
                            visible_filter = (df[xcol] >= xrange[0]) & (df[xcol] <= xrange[1]) & (df[ycol] >= yrange[0]) & (df[ycol] <= yrange[1])
                            set_filter(visible_filter)
                        else:
                            set_filter(None)

                    solara.use_memo(cross_filter, [crossfilter_visible, xrange, yrange])

                    # @solara.use_memo

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


@solara.component
def SummaryCard(df):
    filter, set_filter = use_cross_filter(id(df), "summary")
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


@solara.component
def DropdownCard(df, column=None):
    max_unique = 100
    filter, set_filter = use_cross_filter(id(df), "filter-dropdown")
    columns = use_df_column_names(df)
    column, set_column = solara.use_state(columns[0] if column is None else column)
    uniques = df_unique(df, column, limit=max_unique + 1)
    value, set_value = solara.use_state(None)
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
