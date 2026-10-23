from typing import Any, Optional, Union

import ipyvuetify
import reacton.core
import solara

from ... import data
from ...components.article import Overview


@solara.component
def Page(
    name: Optional[str] = None, page: int = 0, page_size=100
) -> Union[reacton.core.ValueElement[ipyvuetify.Sheet, Any], reacton.core.ValueElement[ipyvuetify.Alert, Any], reacton.core.ValueElement[ipyvuetify.Row, Any]]:
    if name is None:
        with solara.Column() as main:
            solara.Title("Solara demo » Articles")
            Overview()
        return main
    if name not in data.articles:
        return solara.Error(f"No such article: {name!r}")
    article = data.articles[name]
    with solara.ColumnsResponsive(12) as main:
        solara.Title("Solara demo » Article » " + article.title)
        with solara.Link("/article"):
            solara.Text("« Back to overview")
        with solara.Card():
            pre = f"# {article.title}\n\n"
            solara.Markdown(pre + article.markdown)
    return main
