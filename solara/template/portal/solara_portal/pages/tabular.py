"""This Page takes an extra argument, meaning that it can cache urls like /tabular/titanic
and pass the last part of the url as argument to the Page component, so we can render content
dynamically.

The extra page and page_size must be optional arguments, and can be changed using the query parameters, e.g.:
/tabular/titanic?page=1&page_size=50
"""

import solara

from .. import data
from ..components import Layout


@solara.component
def Page(name: str = None, page: int = 0, page_size=100):
    if name is None:
        return solara.Error("Please specify a dataset name, e.g. /tabular/titanic")
    df = data.dfs[name].df
    with Layout() as main:
        solara.DataTable(df=df, page=page, items_per_page=page_size)
        with solara.Head():
            solara.Title(f"Solara demo » table view » {name}")
    return main
