from solara.kitchensink import react, sol, v

from ..data import articles, dfs, names

title = "Solara Example: main"


@react.component
def DataCard(name):
    df = dfs[name].df
    with v.Card(max_width="400px") as main:
        with sol.Link(f"/tabular/{name}"):
            v.Img(height="250", src=dfs[name].image_url)
        v.CardTitle(children=[dfs[name].title])
        with v.CardText():
            sol.Markdown(f"*{len(df):,} rows*")
            with sol.Link(f"/tabular/{name}"):
                sol.Button("Open table view", text=True, icon_name="mdi-table")
    return main


@react.component
def ArticleCard(name):
    article = articles[name]
    with v.Card(max_width="400px") as main:
        with sol.Link(f"/article/{name}"):
            v.Img(height="250", src=article.image_url)
        v.CardTitle(children=[article.title])
        with v.CardText():
            sol.Markdown(article.description)
            with sol.Link(f"/article/{name}"):
                sol.Button("Read article", text=True, icon_name="mdi-book-open")
    return main


@react.component
def PeopleCard(name):
    # article = articles[name]
    with v.Card() as main:
        # with sol.Link(f"/article/{name}"):
        #     v.Img(height="250", src=article.image_url)
        # v.CardTitle(children=[article.title])
        with v.CardText():
            sol.Markdown(f"# {name}")
            sol.Markdown(
                """
   * Age:
   * Height:
"""
            )
            with sol.Link(f"/people/{name}"):
                sol.Button("View employee", text=True, icon_name="mdi-profile")
    return main


@react.component
def Layout(children=[]):
    router = react.use_context(sol.routing.router_context)
    with sol.VBox() as navigation:
        with v.List(dense=True):
            with v.ListItemGroup(v_model=router.path):
                with sol.Link(sol.resolve_path("/")):
                    with sol.ListItem("Home", icon_name="mdi-home", value="/"):
                        pass
                with sol.ListItem("tabular data", icon_name="mdi-database"):
                    for name in names:
                        pathname = f"/tabular/{name}"
                        with sol.Link(sol.resolve_path(pathname)):
                            sol.ListItem(name, value=pathname)
                with sol.ListItem("Articles", icon_name="mdi-book-open"):
                    for name, article in articles.items():
                        pathname = f"/article/{name}"
                        with sol.Link(sol.resolve_path(pathname)):
                            sol.ListItem(article.title, value=pathname)

    with sol.AppLayout(navigation=navigation, title=title, children=children) as main:
        pass
    return main


@react.component
def Page():
    with sol.VBox() as main:
        with sol.Card("Datasets"):
            with v.Container(style_="margin-left: unset; margin-right: unset;"):
                with v.Row(justify="start"):
                    for name in names:
                        with v.Col(sm=4):
                            DataCard(name)

        with v.Container(style_="margin-left: unset; margin-right: unset;"):
            with v.Row():
                with v.Col(style_="display: flex;", sm=6):
                    PeopleCard("Maarten")
                with v.Col(style_="display: flex;", sm=4):
                    with sol.Card("Quick links"):
                        with sol.VBox():
                            for name in names:
                                with sol.Link(f"/viz/scatter/{name}"):
                                    sol.Button(f"Scatter for {name}", text=True)
                                with sol.Link(f"/viz/histogram/{name}"):
                                    sol.Button(f"Histogram for {name}", text=True)

        with sol.Card("Company articles"):
            with v.Container(style_="margin-left: unset; margin-right: unset;"):
                with v.Row(justify="start"):
                    for name in articles:
                        with v.Col():
                            ArticleCard(name)

    return main
