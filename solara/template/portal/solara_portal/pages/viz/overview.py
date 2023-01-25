import solara

from ... import data
from ...components import Layout


@solara.component
def Page(name: str, page: int = 0, page_size=100):
    if name not in data.dfs:
        return solara.Error(f"No such dataframe: {name!r}")
    df = data.dfs[name]
    with Layout() as main:
        solara.DataTable(df=df, page=page, items_per_page=page_size)
    return main
