# import inspect
# import urllib.parse

import solara

title = "Examples"


@solara.component
def Page():
    # show a gallery of all the examples
    router = solara.use_router()
    route_current = router.path_routes[-2]

    for route in route_current.children:
        if route.children:
            solara.Markdown(f"## {route.label}\n" + (route.module.__doc__ or ""))
            with solara.ColumnsResponsive(12, 6, 6, 6, 4):
                for child in route.children:
                    path = route.path + "/" + child.path
                    if child.path in [
                        "tokenizer",
                        "sine",
                        "authorization",
                        "layout_demo",
                        "multipage",
                        "scatter",
                        "scrolling",
                        "tutorial_streamlit",
                        "login_oauth",
                        "pokemon_search",
                        "altair",
                        "bqplot",
                        "ipyleaflet",
                        "calculator",
                        "countdown_timer",
                        "todo",
                    ]:
                        image = route.path + "/" + child.path + ".png"
                        image_url = "https://dxhl76zpt6fap.cloudfront.net/public/examples/" + image
                    else:
                        image_url = "https://dxhl76zpt6fap.cloudfront.net/public/logo.svg"

                    path = getattr(child.module, "redirect", path)
                    if path:
                        with solara.Card(child.label, style="height: 100%;"):
                            with solara.Link(path):
                                with solara.Column(align="center"):
                                    solara.Image(image_url, width="120px" if image_url.endswith(".svg") else "100%")


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

    with solara.HBox(grow=False) as main:
        if route_current.path == "fullscreen":
            with solara.Padding(4, children=children):
                pass
        else:
            with solara.VBox(grow=True, align_items="baseline"):
                doc = module.__doc__
                if doc:
                    with solara.VBox(grow=True):
                        solara.Markdown(doc)
                with solara.HBox():
                    if route_current.path != "/":
                        solara.Button("View source code on GitHub", icon_name="mdi-github-circle", href=github_url, class_="ma-2", target="_blank", text=True)
                        # code = inspect.getsource(module)

                        # code_quoted = urllib.parse.quote_plus(code)
                        # url = f"https://test.solara.dev/try?code={code_quoted}"
                        # solara.Button("Run on solara.dev", icon_name="mdi-pencil", href=url, class_="ma-2", target="_blank")
                # with solara.HBox():
                if not hasattr(module, "Page"):
                    solara.Error(f"No Page component found in {module}")
                else:
                    with solara.Padding(4, children=children):
                        pass
    return main
