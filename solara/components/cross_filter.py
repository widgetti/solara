import operator
from typing import Any, List, cast

import ipyvuetify
import reacton.ipyvuetify as v
import traitlets

import solara
from solara import CellAction, ColumnAction

from ..lab.hooks.dataframe import use_df_column_names
from ..lab.utils.dataframe import (
    df_filter_values,
    df_py_types,
    df_range,
    df_value_count,
)

# to avoid confusing vuetify about selecting 'None' and nothing
magic_value_missing = "__missing_value__"

# first selector is needed in jupyter, which needs to be more specific
# second selector in solara, where there is no need to be more specific (css load order?) and there is not .vuetify-styles
css_message = """
.vuetify-styles .solara-cross-filter-select .v-messages,
.solara-cross-filter-select .v-messages {
    color: #fb8c00;
}
"""


class Select(ipyvuetify.VuetifyTemplate):
    template_file = (__file__, "select.vue")

    value = traitlets.Any().tag(sync=True)
    label = traitlets.Unicode().tag(sync=True)
    clearable = traitlets.Bool().tag(sync=True)
    return_object = traitlets.Bool().tag(sync=True)
    items = traitlets.List().tag(sync=True)
    filtered = traitlets.Bool().tag(sync=True)
    count = traitlets.Int().tag(sync=True)
    multiple = traitlets.Bool().tag(sync=True)
    messages = traitlets.Unicode().tag(sync=True)


@solara.component
def CrossFilterSelect(
    df,
    column: str,
    max_unique: int = 100,
    multiple: bool = False,
    invert=False,
    configurable=True,
    classes: List[str] = [],
):
    """A Select widget that will cross filter a DataFrame.

    See [use_cross_filter](/api/use_cross_filter) for more information about how to use cross filtering.

    ## Arguments

    - `df`: The DataFrame to filter.
    - `column`: The column to filter on.
    - `max_unique`: The maximum number of unique values to show in the dropdown.
    - `multiple`: Whether to allow multiple values to be selected.
    - `invert`: Whether to invert the selection.
    - `configurable`: Whether to show the configuration button.
    - `classes`: Additional CSS classes to add to the main widget.

    """
    import pandas as pd

    filter, set_filter = solara.use_cross_filter(id(df), "filter-dropdown")
    filter_values, set_filter_values = solara.use_state(cast(List[Any], []))
    column, set_column = solara.use_state_or_update(column)
    invert, set_invert = solara.use_state_or_update(invert)
    multiple, set_multiple = solara.use_state_or_update(multiple)

    dff = df
    if filter is not None:
        dff = df[filter]

    value_counts = df_value_count(df, column, limit=max_unique + 1)
    value_counts.rename({"count": "count_max"}, axis=1, inplace=True)

    value_counts_filtered = df_value_count(dff, column, limit=max_unique + 1)
    value_counts = value_counts.merge(value_counts_filtered, how="left", on="value")
    value_counts["count"] = value_counts["count"].fillna(0)
    value_counts["exists"] = value_counts["count"] > 0
    value_counts.sort_values(["exists", "value"], ascending=[False, True], inplace=True)

    columns = use_df_column_names(df)

    def set_values_and_filter(values):
        if values is None:
            set_filter_values([])
            return

        if multiple:
            set_filter_values([value["value"] for value in values])
        else:
            set_filter_values([values["value"]])

    def reset():
        set_filter_values([])

    solara.use_memo(reset, dependencies=[column])

    def update_filter():
        if len(filter_values) == 0:
            set_filter(None)
        else:
            filter_values_without_magic = [None if k == magic_value_missing else k for k in filter_values]
            filter = df_filter_values(df, column, filter_values_without_magic, invert=invert)
            set_filter(filter)

    solara.use_memo(update_filter, dependencies=[filter_values, invert])

    items = [
        {
            "value": magic_value_missing if pd.isna(k.value) else k.value,
            "text": str(k.value) if not pd.isna(k.value) else "NA",
            "count": k.count,
            "count_max": k.count_max,
        }
        for k in value_counts.itertuples()
    ]
    value: Any = None
    if not multiple:
        value = {"value": filter_values[0]} if len(filter_values) > 0 else None
    else:
        value = [{"value": k} for k in filter_values]
    # TODO: reacton bug, we cannot add this under any component context manager
    # this gives an error, probably because the button is added twice
    with v.Btn(v_on="x.on", icon=True) as btn:
        v.Icon(children=["mdi-settings"])
    with solara.VBox(classes=classes) as main:
        solara.Style(css_message)
        with solara.HBox(align_items="baseline"):
            label = f"Select values in {column} having values:" if not invert else f"Drop values in {column} having values:"
            Select.element(
                value=value,
                items=items,
                on_value=set_values_and_filter,
                label=label,
                clearable=True,
                return_object=True,
                multiple=multiple,
                filtered=filter is not None,
                count=len(dff),
                messages=f"Too many unique values, will only show the first {max_unique}" if len(value_counts) > max_unique else "",
                class_="solara-cross-filter-select",
            )
            if configurable:
                with v.Menu(v_slots=[{"name": "activator", "variable": "x", "children": btn}], close_on_content_click=False):
                    with v.Sheet():
                        with v.Container(py_0=True, px_3=True, ma_0=True):
                            with v.Row():
                                with v.Col():
                                    v.Select(v_model=column, items=columns, on_v_model=set_column, label="Choose column")
                                    v.Switch(v_model=invert, on_v_model=set_invert, label="Invert filter")
                                    v.Switch(v_model=multiple, on_v_model=set_multiple, label="Select multiple")

    return main


@solara.component
def CrossFilterReport(df, classes: List[str] = []):
    """Shows a report of the current cross filter state.

    Shows number of rows filtered, and the total number of rows.

    See [use_cross_filter](/api/use_cross_filter) for more information about how to use cross filtering.

    ## Arguments

    - `df`: The DataFrame where the filter is applied to.
    - `classes`: Additional CSS classes to add to the main widget.

    """
    filter, set_filter = solara.use_cross_filter(id(df), "summary")
    dff = df
    filtered = False
    if filter is not None:
        filtered = True
        dff = df[filter]
    progress = len(dff) / len(df) * 100
    with solara.VBox(classes=classes) as main:
        with solara.HBox(align_items="center"):
            icon = "mdi-filter"
            v.Icon(children=[icon], style_="opacity: 0.1" if not filtered else "")
            if filtered:
                summary = f"{len(dff):,} / {len(df):,}"
            else:
                summary = f"{len(dff):,}"
            v.Html(tag="h3", children=[summary], style_="display: inline")
        # always add a progress bar to make sure the layout is the same
        if filtered:
            v.ProgressLinear(value=progress).key("visible")
        else:
            v.ProgressLinear(value=0, style_="visibility: hidden").key("hidden")

    return main


@solara.component
def CrossFilterSlider(
    df,
    column: str,
    invert=False,
    enable: bool = True,
    mode: str = "==",
    configurable=True,
):
    """A Slider widget that will cross filter a DataFrame.

    See [use_cross_filter](/api/use_cross_filter) for more information about how to use cross filtering.

    ## Arguments

    - `df`: The DataFrame to filter.
    - `column`: The column to filter on.
    - `invert`: If True, the filter will be inverted.
    - `enable`: If False, the filter will be disabled.
    - `mode`: The mode to use for filtering. Can be one of `==`, `>=`, `<=`, `>`, `<`.
    - `configurable`: Whether to show a configuration button.

    """
    filter, set_filter = solara.use_cross_filter(id(df), "filter-slider")
    filter_value, set_filter_value = solara.use_state(None)
    column, set_column = solara.use_state_or_update(column)
    invert, set_invert = solara.use_state_or_update(invert)
    enable, set_enable = solara.use_state_or_update(enable)
    mode, set_mode = solara.use_state_or_update(mode)

    # TODO: should we use the filter for min/max?
    # dff = df
    # if filter is not None:
    #     dff = df[filter]

    vmin, vmax = df_range(df, column)

    columns = use_df_column_names(df)
    py_types = df_py_types(df)
    columns_numeric = [c for c in columns if py_types[c] in [int, float]]

    def reset():
        set_filter_value(vmin)

    solara.use_memo(reset, dependencies=[column])

    def update_filter():
        if not enable or filter_value is None:
            set_filter(None)
        else:
            operator_map = {
                "==": operator.eq,
                ">=": operator.ge,
                "<=": operator.le,
                ">": operator.gt,
                "<": operator.lt,
                "!=": operator.ne,
            }
            filter = operator_map[mode](df[column], filter_value)
            if invert:
                filter = ~filter
            set_filter(filter)

    solara.use_memo(update_filter, dependencies=[filter_value, invert, enable, mode])

    # TODO: reacton bug, see CrossFilterSelect
    with v.Btn(v_on="x.on", icon=True) as btn:
        v.Icon(children=["mdi-settings"])

    with solara.VBox() as main:
        with solara.HBox(align_items="center"):
            label = f"Select {column} {mode} " if not invert else f"Drop {column} {mode} "

            if py_types[column] == int:
                if isinstance(filter_value, int):
                    solara.SliderInt(label=label, value=filter_value, min=vmin, max=vmax, on_value=set_filter_value, disabled=not enable, thumb_label=False)
                else:
                    solara.Error(f"Filter value is not an integer type, but {type(filter_value)} (value = {filter_value})")
                if filter_value is not None:
                    solara.Text(f"{filter_value:,}")
            elif py_types[column] == float:
                if isinstance(filter_value, float):
                    solara.SliderFloat(label=label, value=filter_value, min=vmin, max=vmax, on_value=set_filter_value, disabled=not enable, thumb_label=False)
                else:
                    solara.Error(f"Filter value is not an floating point type, but {type(filter_value)} (value = {filter_value})")
                if filter_value is not None:
                    solara.Text(f"{filter_value:,}")
            else:
                solara.Warning(f"{py_types[column]} not supported for Slider")

            if configurable:
                with v.Menu(v_slots=[{"name": "activator", "variable": "x", "children": btn}], close_on_content_click=False):
                    with v.Sheet():
                        with v.Container(py_0=True, px_3=True, ma_0=True):
                            with v.Row():
                                with v.Col():
                                    columns_numeric = [c for c in columns if py_types[c] in [int, float]]
                                    v.Select(v_model=column, items=columns_numeric, on_v_model=set_column, label="Choose column")
                                    v.Switch(v_model=invert, on_v_model=set_invert, label="Invert filter")
                                    v.Switch(v_model=enable, on_v_model=set_enable, label="Enable filter")
                                    with solara.ToggleButtonsSingle(value=mode, on_value=set_mode):  # type: ignore
                                        solara.Button(icon_name="mdi-code-equal", icon=True, value="==")
                                        solara.Button(icon_name="mdi-code-not-equal", icon=True, value="!=")
                                        solara.Button(icon_name="mdi-code-less-than", icon=True, value="<")
                                        solara.Button(icon_name="mdi-code-less-than-or-equal", icon=True, value="<=")
                                        solara.Button(icon_name="mdi-code-greater-than", icon=True, value=">")
                                        solara.Button(icon_name="mdi-code-greater-than-or-equal", icon=True, value=">=")

    return main


@solara.component
def CrossFilterDataFrame(df, items_per_page=20, column_actions: List[ColumnAction] = [], cell_actions: List[CellAction] = [], scrollable=False):
    """Display a DataFrame with filters applied from the cross filter.

    This component wraps [DataFrame](/api/dataframe).

    See [use_cross_filter](/api/use_cross_filter) for more information about how to use cross filtering.

    # Arguments

     * `df` - a Pandas dataframe.
     * `column_actions` - Triggered via clicking on the triple dot icon on the headers (visible when hovering).
     * `cell_actions` -  Triggered via clicking on the triple dot icon in the cell (visible when hovering).

    """
    dff = df
    filter, set_filter = solara.use_cross_filter(id(df), "dataframe")
    if filter is not None:
        dff = df[filter]
    return solara.DataFrame(dff, items_per_page=items_per_page, scrollable=scrollable, column_actions=column_actions, cell_actions=cell_actions)
