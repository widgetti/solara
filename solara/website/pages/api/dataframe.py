"""
# DataFrame

"""

from typing import Any, Dict, Optional, cast

import plotly

import solara
from solara.website.utils import apidoc

df = plotly.data.iris()


@solara.component
def Page():
    column, set_column = solara.use_state(cast(Optional[str], None))
    cell, set_cell = solara.use_state(cast(Dict[str, Any], {}))

    def on_action_column(column):
        set_column(column)

    def on_action_cell(column, row_index):
        set_cell(dict(column=column, row_index=row_index))

    column_actions = [solara.ColumnAction(icon="mdi-sunglasses", name="User column action", on_click=on_action_column)]
    cell_actions = [solara.CellAction(icon="mdi-white-balance-sunny", name="User cell action", on_click=on_action_cell)]
    solara.Markdown(
        f"""
        ## Demo

        Below we show display the titanic dataset, and demonstrate a user column and cell action. Try clicking on the triple icon when hovering
        above a column or cell. And see the following values changes:

        * Column action on: `{column}`
        * Cell action on: `{cell}`

    """
    )
    solara.DataFrame(df, column_actions=column_actions, cell_actions=cell_actions)


__doc__ += apidoc(solara.DataFrame.f)  # type: ignore
