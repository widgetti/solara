from typing import Callable

from solara.alias import react, rv, sol


@react.component
def Header(
    on_toggle_left_menu: Callable[[], None] = None,
    on_toggle_right_menu: Callable[[], None] = None,
):
    # use routes of parent (assuming we are a child of a layout)
    route_current, all_routes = sol.use_route(level=-1)

    # set states for menu
    with rv.AppBar(tag="header", flat=True, class_="bg-primary-fade padding-40", height="auto") as main:
        with rv.ToolbarTitle(class_="d-flex", style_="align-items:center"):
            with sol.Button(icon=True, class_="hidden-md-and-up", on_click=lambda: on_toggle_left_menu and on_toggle_left_menu()):
                rv.Icon(children=["mdi-menu"])
            with sol.Link(path_or_route="/"):
                sol.Image("/static/assets/images/logo.svg")
        rv.Spacer()

        # menu
        with rv.Html(tag="ul", class_="main-menu menu d-none d-md-flex"):
            for route in all_routes:
                current = route_current == route
                with rv.Html(tag="li", class_="active" if current else None):
                    sol.Link("/" + route.path, children=[route.label])
        with rv.Btn(icon=True, tag="a", class_="d-none d-md-flex", attributes={"href": sol.github_url, "target": "_blank"}):
            rv.Icon(children=["mdi-github-circle"])

        if route_current and len(route_current.children) > 0:
            with sol.Button(icon=True, class_="hidden-md-and-up", on_click=lambda: on_toggle_right_menu and on_toggle_right_menu()):
                rv.Icon(children=["mdi-menu"])

    return main
