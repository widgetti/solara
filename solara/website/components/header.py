from typing import Callable

import solara
from solara.alias import rv
from solara.server import settings


@solara._component_vue("algolia.vue")
def Algolia(app_id: str, index_name: str, api_key: str, debug=False):
    pass


@solara.component
def Header(
    on_toggle_left_menu: Callable[[], None] = None,
    on_toggle_right_menu: Callable[[], None] = None,
):
    # use routes of parent (assuming we are a child of a layout)
    route_current, all_routes = solara.use_route(level=-1)
    router = solara.use_router()

    # set states for menu
    with rv.AppBar(tag="header", flat=True, class_="bg-primary-fade padding-40", height="auto") as main:
        with rv.ToolbarTitle(class_="d-flex", style_="align-items:center"):
            if route_current and len(route_current.children) > 0:
                with solara.Button(icon=True, class_="hidden-md-and-up", on_click=lambda: on_toggle_left_menu and on_toggle_left_menu()):
                    rv.Icon(children=["mdi-menu"])
            with solara.Link(path_or_route="/"):
                solara.Image(router.root_path + "/static/assets/images/logo.svg")
        rv.Spacer()

        if settings.search.enabled:
            from solara_enterprise.search.search import Search

            Search()
        Algolia(app_id="9KW9L7O5EQ", api_key="ef7495102afff1e16d1b7cf6ec2ab2d0", index_name="solara", debug=True)
        # menu
        with rv.Html(tag="ul", class_="main-menu menu d-none d-md-flex"):
            for route in all_routes:
                if route.path == "apps":
                    continue
                current = route_current == route
                with rv.Html(tag="li", class_="active" if current else None):
                    solara.Link("/" + route.path if route.path != "/" else "/", children=[route.label])
        with rv.Btn(icon=True, tag="a", class_="d-none d-md-flex", attributes={"href": solara.github_url, "target": "_blank"}):
            rv.Icon(children=["mdi-github-circle"])

        with rv.Btn(icon=True, tag="a", class_="d-none d-md-flex", attributes={"href": "https://discord.gg/MEpm6sEjdq", "target": "_blank"}):
            rv.Icon(children=["mdi-discord"])

        with solara.Button(icon=True, class_="hidden-md-and-up", on_click=lambda: on_toggle_right_menu and on_toggle_right_menu()):
            rv.Icon(children=["mdi-menu"])

    return main
