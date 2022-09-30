from dataclasses import replace
from typing import List

import solara
import solara.hooks.dataframe

from .. import CellAction, ColumnAction
from ..widgets import DataTable as DataTableWidget


def format_default(df, column, row_index, value):
    return str(value)


@solara.component
def DataTable(df, page=0, items_per_page=20, format=None, column_actions: List[ColumnAction] = [], cell_actions: List[CellAction] = [], scrollable=False):
    total_length = len(df)
    options = {"descending": False, "page": page + 1, "itemsPerPage": items_per_page, "sortBy": [], "totalItems": total_length}
    options, set_options = solara.use_state(options, key="options")
    format = format or format_default
    # frontend does 1 base, we use 0 based
    page = options["page"] - 1
    items_per_page = options["itemsPerPage"]
    i1 = page * items_per_page
    i2 = min(total_length, (page + 1) * items_per_page)

    columns = solara.hooks.dataframe.use_df_column_names(df)

    items = []
    column_data = {}
    dfs = df[i1:i2]

    if solara.hooks.dataframe.df_type(df) == "pandas":
        column_data = dfs[columns].to_dict("records")
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
    )


@solara.component
def DataFrame(df, column_actions: List[ColumnAction] = [], cell_actions: List[CellAction] = []):
    """Displays a Pandas dataframe in a table.


    ## Arguments

     * `df` - `DataFrame` - a Pandas dataframe.
     * `column_actions` - Triggered via clicking on the triple dot icon on the headers (visible when hovering).
     * `cell_actions` -  Triggered via clicking on the triple dot icon in the cell (visible when hovering).


    """
    return DataTable(df, column_actions=column_actions, cell_actions=cell_actions)
