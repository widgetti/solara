import solara
from solara.website.components import Gallery, MarkdownWithMetadata

title = "Examples"

pycafe_projects = [
    "chatbot",
    "tokenizer",
]


@solara.component
def Page(route_external=None):
    Gallery(route_external)


@solara.component
def Layout(children):
    # TODO: this is using a private API, what is the best way to do this?
    # we want to 'eat' the whole route for the current level, and the level below
    # for example the utilities directory. But if an example does routing, we don't want
    # to take on that route.
    router = solara.use_router()
    route_current = router.path_routes[-1]
    # route_current, all_routes = solara.use_route()

    if route_current is None:
        return solara.Error("Page not found")
    module = route_current.module
    assert module is not None
    github_url = solara.util.github_url(module.__file__)

    if route_current.path == "fullscreen":
        with solara.Padding(4, children=children):
            pass
    else:
        with solara.Column(align="center", style={"max-width": "100%"}):
            doc = module.__doc__
            if doc:
                with solara.Column():
                    MarkdownWithMetadata(doc)
            with solara.Column(style={"max-width": "min(100%, 1024px)", "width": "100%"}):
                if route_current.path != "/":
                    solara.Button("View source code on GitHub", icon_name="mdi-github-circle", href=github_url, class_="ma-2", target="_blank", text=True)
                if route_current.path in pycafe_projects:
                    pycafe_url = f"https://py.cafe/solara/{route_current.path}"
                    solara.Button(
                        "Run this example on PyCafe", icon_name="mdi-coffee-to-go-outline", href=pycafe_url, class_="ma-2", target="_blank", text=True
                    )
                if not hasattr(module, "Page"):
                    solara.Error(f"No Page component found in {module}")
                else:
                    with solara.Div(children=children):
                        pass
