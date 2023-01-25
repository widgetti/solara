"""This Page takes an extra argument, meaning that it can cache urls like /tabular/titanic
and pass the last part of the url as argument to the Page component, so we can render content
dynamically.
"""

from typing import Optional

import solara

from .. import data
from ..components import data as data_components


@solara.component
def Page(name: Optional[str] = None, page: int = 0, page_size=100):
    if name is None or name not in data.dfs:
        with solara.Column() as main:
            solara.Title("Solara demo » table view")
            data_components.Overview()
        return main

    df = data.dfs[name].df
    with solara.ColumnsResponsive(12) as main:
        with solara.Link("/tabular"):
            solara.Text("« Back to overview")
        solara.DataTable(df=df, page=page, items_per_page=page_size)
        with solara.Head():
            solara.Title(f"Solara demo » table view » {name}")
    return main
