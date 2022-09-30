import solara
from solara.alias import rv

from ..data import articles, dfs, names

title = "Solara Example: main"


@solara.component
def DataCard(name):
    df = dfs[name].df
    with rv.Card(max_width="400px") as main:
        with solara.Link(f"/tabular/{name}"):
            rv.Img(height="250", src=dfs[name].image_url)
        rv.CardTitle(children=[dfs[name].title])
        with rv.CardText():
            solara.Markdown(f"*{len(df):,} rows*")
            with solara.Link(f"/tabular/{name}"):
                solara.Button("Open table view", text=True, icon_name="mdi-table")
    return main


@solara.component
def ArticleCard(name):
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
def PeopleCard(name):
    # article = articles[name]
    with rv.Card() as main:
        # with solara.Link(f"/article/{name}"):
        #     rv.Img(height="250", src=article.image_url)
        # rv.CardTitle(children=[article.title])
        with rv.CardText():
            solara.Markdown(f"# {name}")
            solara.Markdown(
                """
   * Age:
   * Height:
"""
            )
            with solara.Link(f"/people/{name}"):
                solara.Button("View employee", text=True, icon_name="mdi-profile")
    return main


@solara.component
def Layout(children=[]):
    router = solara.use_context(solara.routing.router_context)
    with solara.VBox() as navigation:
        with rv.List(dense=True):
            with rv.ListItemGroup(v_model=router.path):
                with solara.Link(solara.resolve_path("/")):
                    with solara.ListItem("Home", icon_name="mdi-home", value="/"):
                        pass
                with solara.ListItem("tabular data", icon_name="mdi-database"):
                    for name in names:
                        pathname = f"/tabular/{name}"
                        with solara.Link(solara.resolve_path(pathname)):
                            solara.ListItem(name, value=pathname)
                with solara.ListItem("Articles", icon_name="mdi-book-open"):
                    for name, article in articles.items():
                        pathname = f"/article/{name}"
                        with solara.Link(solara.resolve_path(pathname)):
                            solara.ListItem(article.title, value=pathname)

    with solara.AppLayout(navigation=navigation, title=title, children=children) as main:
        pass
    return main


@solara.component
def Page():
    with solara.VBox() as main:
        with solara.Card("Datasets"):
            with rv.Container(style_="margin-left: unset; margin-right: unset;"):
                with rv.Row(justify="start"):
                    for name in names:
                        with rv.Col(sm=4):
                            DataCard(name)

        with rv.Container(style_="margin-left: unset; margin-right: unset;"):
            with rv.Row():
                with rv.Col(style_="display: flex;", sm=6):
                    PeopleCard("Maarten")
                with rv.Col(style_="display: flex;", sm=4):
                    with solara.Card("Quick links"):
                        with solara.VBox():
                            for name in names:
                                with solara.Link(f"/viz/scatter/{name}"):
                                    solara.Button(f"Scatter for {name}", text=True)
                                with solara.Link(f"/viz/histogram/{name}"):
                                    solara.Button(f"Histogram for {name}", text=True)

        with solara.Card("Company articles"):
            with rv.Container(style_="margin-left: unset; margin-right: unset;"):
                with rv.Row(justify="start"):
                    for name in articles:
                        with rv.Col():
                            ArticleCard(name)

    return main
