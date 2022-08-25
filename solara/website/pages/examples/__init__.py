import inspect
import urllib.parse
from typing import cast

from solara.alias import react, sol

title = "Examples"


@react.component
def Page():
    # TODO: put a gallery here?
    return sol.Markdown("Click an example on the left")


@react.component
def ExtraLayout(children):
    # level -1 causes us to get the routes of our parent
    route_current, all_routes = sol.use_route(level=-1)

    if route_current is None:
        return sol.Error("Page not found")
    module = route_current.module
    assert module is not None
    github_url = sol.util.github_url(module.__file__)
    with sol.Card(margin=4) as main:
        with sol.HBox(grow=False):
            with sol.VBox(grow=False):
                with sol.HBox():
                    if route_current.path != "/":
                        sol.Button("View on GitHub", icon_name="mdi-git", href=github_url, class_="ma-2", target="_blank")
                        code = inspect.getsource(module)

                        code_quoted = urllib.parse.quote_plus(code)
                        url = f"https://test.solara.dev/try?code={code_quoted}"
                        sol.Button("Run on solara.dev", icon_name="mdi-pencil", href=url, class_="ma-2", target="_blank")
                if not hasattr(module, "Page"):
                    sol.Error(f"No Page component found in {module}")
                else:
                    with sol.Padding(4):
                        component = cast(react.core.Component, module.Page)
                        component()
    return main


@react.component
def Layout(children=[]):
    with sol.TabNavigation(vertical=True) as main:
        ExtraLayout(children=children)
    return main
