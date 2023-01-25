import solara
from solara.alias import rv

from ..components import article, data
from ..data import articles, names


@solara.component
def PeopleCard(name):
    with solara.Card(f"Employee of the Month: {name}") as main:
        with rv.CardText():
            solara.Markdown(
                """
                * Department: foo
                * Skills: bar, baz
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
                    for name, article_ in articles.items():
                        pathname = f"/article/{name}"
                        with solara.Link(solara.resolve_path(pathname)):
                            solara.ListItem(article_.title, value=pathname)

    with solara.AppLayout(navigation=navigation, title="Solara demo", children=children) as main:
        pass
    return main


@solara.component
def Page():
    with solara.VBox() as main:
        solara.Title("Solara demo » Home")
        data.Overview()
        article.Overview()

        with solara.ColumnsResponsive(12):
            with solara.Card("Other"):
                with solara.ColumnsResponsive(6):
                    PeopleCard("Maarten Breddels")
                    with solara.Card("Quick links"):
                        with solara.Column():
                            for name in names:
                                with solara.Link(f"/viz/scatter/{name}"):
                                    solara.Button(f"Scatter for {name}", text=True)
                                with solara.Link(f"/viz/histogram/{name}"):
                                    solara.Button(f"Histogram for {name}", text=True)

    return main
