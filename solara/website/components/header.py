from typing import Callable

import solara
from solara.alias import rv


@solara.component
def Header(
    on_toggle_left_menu: Callable[[], None] = None,
    on_toggle_right_menu: Callable[[], None] = None,
):
    # use routes of parent (assuming we are a child of a layout)
    route_current, all_routes = solara.use_route(level=-1)

    # set states for menu
    with rv.AppBar(tag="header", flat=True, class_="bg-primary-fade padding-40", height="auto") as main:
        with rv.ToolbarTitle(class_="d-flex", style_="align-items:center"):
            with solara.Button(icon=True, class_="hidden-md-and-up", on_click=lambda: on_toggle_left_menu and on_toggle_left_menu()):
                rv.Icon(children=["mdi-menu"])
            with solara.Link(path_or_route="/"):
                solara.Image("./static/assets/images/logo.svg")
        rv.Spacer()

        # menu
        with rv.Html(tag="ul", class_="main-menu menu d-none d-md-flex"):
            for route in all_routes:
                current = route_current == route
                with rv.Html(tag="li", class_="active" if current else None):
                    solara.Link("/" + route.path, children=[route.label])
        with rv.Btn(icon=True, tag="a", class_="d-none d-md-flex", attributes={"href": solara.github_url, "target": "_blank"}):
            rv.Icon(children=["mdi-github-circle"])

        if route_current and len(route_current.children) > 0:
            with solara.Button(icon=True, class_="hidden-md-and-up", on_click=lambda: on_toggle_right_menu and on_toggle_right_menu()):
                rv.Icon(children=["mdi-menu"])

    return main
