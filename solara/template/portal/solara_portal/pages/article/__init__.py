from solara.kitchensink import react, sol

from ... import data
from ...components import Layout


@react.component
def Page(name: str, page: int = 0, page_size=100):
    # router = sol.use_router()
    if name not in data.articles:
        return sol.Error(f"No such article: {name!r}")
    article = data.articles[name]
    with Layout() as main:
        with sol.Card():
            pre = f"# {article.title}\n\n"
            sol.Markdown(pre + article.markdown)
    return main
