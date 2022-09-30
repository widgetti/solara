import inspect
import urllib.parse

import solara

title = "Examples"


@solara.component
def Page():
    # TODO: put a gallery here?
    return solara.Markdown("Click an example on the left")


@solara.component
def Layout(children):
    route_current, all_routes = solara.use_route()

    if route_current is None:
        return solara.Error("Page not found")
    module = route_current.module
    assert module is not None
    github_url = solara.util.github_url(module.__file__)

    with solara.HBox(grow=False) as main:
        with solara.VBox(grow=True):
            with solara.HBox():
                if route_current.path != "/":
                    solara.Button("View on GitHub", icon_name="mdi-git", href=github_url, class_="ma-2", target="_blank")
                    code = inspect.getsource(module)

                    code_quoted = urllib.parse.quote_plus(code)
                    url = f"https://test.solara.dev/try?code={code_quoted}"
                    solara.Button("Run on solara.dev", icon_name="mdi-pencil", href=url, class_="ma-2", target="_blank")
            if not hasattr(module, "Page"):
                solara.Error(f"No Page component found in {module}")
            else:
                with solara.Padding(4, children=children):
                    pass
    return main
