"""
# DataTable

The DataTable component can render dataframes of any size due to pagination.

## API

### Component signature
```python
@react.component
def DataTable(df, page=0, items_per_page=20, format=None, column_actions: List[ColumnAction] = [], cell_actions: List[CellAction] = []):
    ...
```

### arguments

* `df` - `DataFrame`

### events

* `column_actions` - Triggered via clicking on the triple dot icon on the headers (visible when hovering).
* `cell_actions` -  Triggered via clicking on the triple dot icon in the cell (visible when hovering).

"""

from typing import Any, Dict, Optional, cast

import vaex

import solara.components.datatable
from solara.kitchensink import react, sol

df = vaex.datasets.titanic()


@react.component
def DataTableDemo():
    column, set_column = react.use_state(cast(Optional[str], None))
    cell, set_cell = react.use_state(cast(Dict[str, Any], {}))

    def on_action_column(column):
        set_column(column)

    def on_action_cell(column, row_index):
        set_cell(dict(column=column, row_index=row_index))

    column_actions = [sol.ColumnAction(icon="mdi-sunglasses", name="User column action", on_click=on_action_column)]
    cell_actions = [sol.CellAction(icon="mdi-white-balance-sunny", name="User cell action", on_click=on_action_cell)]
    with sol.Div() as main:
        sol.MarkdownIt(
            f"""
            ## Demo

            Below we show display the titanic dataset, and demonstrate a user colum and cell action. Try clicking on the triple icon when hovering
            above a column or cell. And see the following values changes:

            * Column action on: `{column}`
            * Cell action on: `{cell}`

        """
        )
        sol.components.datatable.DataTable(df, column_actions=column_actions, cell_actions=cell_actions)
    return main


Component = solara.components.datatable.DataTable
App = DataTableDemo
