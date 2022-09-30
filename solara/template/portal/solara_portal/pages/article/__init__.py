import solara

from ... import data
from ...components import Layout


@solara.component
def Page(name: str, page: int = 0, page_size=100):
    # router = solara.use_router()
    if name not in data.articles:
        return solara.Error(f"No such article: {name!r}")
    article = data.articles[name]
    with Layout() as main:
        with solara.Card():
            pre = f"# {article.title}\n\n"
            solara.Markdown(pre + article.markdown)
    return main
