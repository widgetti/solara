import dataclasses
import math
import os
from dataclasses import replace
from typing import Callable, List, Optional

import ipyvuetify as v
import ipywidgets
import traitlets

import solara
import solara.hooks.dataframe
import solara.lab
from solara.lab.hooks.dataframe import use_df_column_names
from solara.lab.utils.dataframe import df_type

from .. import CellAction, ColumnAction


def _ensure_dict(d):
    if dataclasses.is_dataclass(d):
        return dataclasses.asdict(d)
    return d


def _drop_keys_from_list_of_mappings(drop):
    def closure(list_of_dicts, widget):
        return [{k: v for k, v in _ensure_dict(d).items() if k not in drop} for d in list_of_dicts]

    return closure


class DataTableWidget(v.VuetifyTemplate):
    template_file = os.path.realpath(os.path.join(os.path.dirname(__file__), "datatable.vue"))

    total_length = traitlets.CInt().tag(sync=True)
    checked = traitlets.List([]).tag(sync=True)  # indices of which rows are selected
    column_actions = traitlets.List(trait=traitlets.Instance(ColumnAction), default_value=[]).tag(
        sync=True, to_json=_drop_keys_from_list_of_mappings(["on_click"])
    )
    _column_actions_callbacks = traitlets.List(trait=traitlets.Callable(), default_value=[])
    cell_actions = traitlets.List(trait=traitlets.Instance(CellAction), default_value=[]).tag(sync=True, to_json=_drop_keys_from_list_of_mappings(["on_click"]))
    _cell_actions_callbacks = traitlets.List(trait=traitlets.Callable(), default_value=[])
    items = traitlets.Any().tag(sync=True)  # the data, a list of dict
    headers = traitlets.Any().tag(sync=True)
    headers_selections = traitlets.Any().tag(sync=True)
    options = traitlets.Any().tag(sync=True)
    items_per_page = traitlets.CInt(11).tag(sync=True)
    selections = traitlets.Any([]).tag(sync=True)
    selection_colors = traitlets.Any([]).tag(sync=True)
    selection_enabled = traitlets.Bool(True).tag(sync=True)
    highlighted = traitlets.Int(None, allow_none=True).tag(sync=True)
    scrollable = traitlets.Bool(False).tag(sync=True)

    # for use with scrollable, when used in the default UI
    height = traitlets.Unicode(None, allow_none=True).tag(sync=True)

    hidden_components = traitlets.List([]).tag(sync=False)
    column_header_hover = traitlets.Unicode(allow_none=True).tag(sync=True)
    column_header_widget = traitlets.Any(allow_none=True).tag(sync=True, **ipywidgets.widget_serialization)

    def vue_on_column_action(self, data):
        header_value, action_index = data
        on_click = self._column_actions_callbacks[action_index]
        if on_click:
            on_click(header_value)

    def vue_on_cell_action(self, data):
        row, header_value, action_index = data
        on_click = self._cell_actions_callbacks[action_index]
        if on_click:
            on_click(header_value, row)


def format_default(df, column, row_index, value):
    if isinstance(value, float) and math.isnan(value):
        return "NaN"
    return str(value)


@solara.component
def DataTable(
    df,
    page=0,
    items_per_page=20,
    format=None,
    column_actions: List[ColumnAction] = [],
    cell_actions: List[CellAction] = [],
    scrollable=False,
    on_column_header_hover: Optional[Callable[[Optional[str]], None]] = None,
    column_header_info: Optional[solara.Element] = None,
):
    total_length = len(df)
    options = {"descending": False, "page": page + 1, "itemsPerPage": items_per_page, "sortBy": [], "totalItems": total_length}
    options, set_options = solara.use_state(options, key="options")
    format = format or format_default
    # frontend does 1 base, we use 0 based
    page = options["page"] - 1
    items_per_page = options["itemsPerPage"]
    i1 = page * items_per_page
    i2 = min(total_length, (page + 1) * items_per_page)

    columns = use_df_column_names(df)

    items = []
    column_data = {}
    dfs = df[i1:i2]

    if df_type(df) == "pandas":
        column_data = dfs[columns].to_dict("records")
    elif df_type(df) == "polars":
        column_data = dfs[columns].to_dicts()
    else:
        column_data = dfs[columns].to_records()
    for i in range(i2 - i1):
        item = {"__row__": i + i1}  # special key for the row number
        for column in columns:
            item[column] = format(dfs, column, i + i1, column_data[i][column])
        items.append(item)

    headers = [{"text": name, "value": name, "sortable": False} for name in columns]
    column_actions_callbacks = [k.on_click for k in column_actions]
    cell_actions_callbacks = [k.on_click for k in cell_actions]
    column_actions = [replace(k, on_click=None) for k in column_actions]
    cell_actions = [replace(k, on_click=None) for k in cell_actions]

    return DataTableWidget.element(
        total_length=total_length,
        items=items,
        headers=headers,
        headers_selections=[],
        options=options,
        items_per_page=items_per_page,
        selections=[],
        selection_colors=[],
        selection_enabled=False,
        highlighted=None,
        scrollable=scrollable,
        on_options=set_options,
        column_actions=column_actions,
        cell_actions=cell_actions,
        _column_actions_callbacks=column_actions_callbacks,
        _cell_actions_callbacks=cell_actions_callbacks,
        on_column_header_hover=on_column_header_hover,
        column_header_widget=column_header_info,
    )


@solara.component
def DataFrame(
    df,
    items_per_page=20,
    column_actions: List[ColumnAction] = [],
    cell_actions: List[CellAction] = [],
    scrollable=False,
    on_column_header_hover: Optional[Callable[[Optional[str]], None]] = None,
    column_header_info: Optional[solara.Element] = None,
):
    """Displays a Pandas dataframe in a table.

    Pass in a dataframe as first argument, and optionally how many items per page to display.

    ```solara
    import solara
    import pandas as pd
    import plotly

    df = plotly.data.iris()

    @solara.component
    def Page():
        solara.DataFrame(df, items_per_page=5)

    ```

    # Custom column header info

    Use the `column_header_info` argument to display a custom component on the column header when
    the user hover above it. In this case we display the value counts for the column.

    ```solara
    import solara
    import pandas as pd
    import plotly

    df = plotly.data.iris()

    @solara.component
    def Page():
        column_hover, set_column_hover = solara.use_state(None)

        with solara.Column(margin=4) as column_header_info:
            if column_hover:
                solara.Text("Value counts for " + column_hover)
                display(df[column_hover].value_counts())
            # if no column is hovered above, we provide an empty container
            # so we always see the triple dot icon on the column header

        solara.DataFrame(df, column_header_info=column_header_info, on_column_header_hover=set_column_hover)
    ```


    ## Arguments

     * `df` - `DataFrame` - a Pandas dataframe.
     * `items_per_page` - `int` - number of items per page.
     * `column_actions` - Triggered via clicking on the triple dot icon on the headers (visible when hovering).
     * `cell_actions` -  Triggered via clicking on the triple dot icon in the cell (visible when hovering).
     * `on_column_header_hover` - Optional callback when the user hovers over the triple dot icon on a header.
     * `column_header_info` - Element to display in the column menu popup (visible when hovering), provide an
            empty container element (like [Column](/api/column)) to force showing the trigle dot icon (see example).

    """
    return DataTable(
        df,
        items_per_page=items_per_page,
        column_actions=column_actions,
        cell_actions=cell_actions,
        scrollable=scrollable,
        on_column_header_hover=on_column_header_hover,
        column_header_info=column_header_info,
    )
