from typing import Any

import ipyvuetify
import reacton.core
import reacton.ipyvuetify as rv
import solara

from ..data import articles


@solara.component
def ArticleCard(name) -> reacton.core.ValueElement[ipyvuetify.Card, Any]:
    article = articles[name]
    with rv.Card(max_width="400px") as main:
        with solara.Link(f"/article/{name}"):
            rv.Img(height="250", src=article.image_url)
        rv.CardTitle(children=[article.title])
        with rv.CardText():
            solara.Markdown(article.description)
            with solara.Link(f"/article/{name}"):
                solara.Button("Read article", text=True, icon_name="mdi-book-open")
    return main


@solara.component
def Overview() -> reacton.core.ValueElement[ipyvuetify.Row, Any]:
    with solara.ColumnsResponsive(12) as main:
        with solara.Card("Company articles"):
            with solara.ColumnsResponsive(12, small=6, large=4):
                for name in articles:
                    ArticleCard(name)
    return main
