from solara.kitchensink import react, sol

from ... import data
from ...components import Layout


@react.component
def Page(name: str, page: int = 0, page_size=100):
    # router = sol.use_router()
    if name not in data.dfs:
        return sol.Error(f"No such dataframe: {name!r}")
    df = data.dfs[name]
    with Layout() as main:
        sol.DataTable(df=df, page=page, items_per_page=page_size)
        # page_size = sol.Select(page_size).use()
        # router.set_query(page=page, page_size=page_size)
    return main
