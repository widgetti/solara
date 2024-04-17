from typing import Callable

import solara
import solara.lab
from solara.alias import rv
from solara.server import settings
from .algolia import Algolia


@solara.component
def Header(
    on_toggle_left_menu: Callable[[], None] = None,
    on_toggle_right_menu: Callable[[], None] = None,
):
    # use routes of parent (assuming we are a child of a layout)
    route_current, all_routes = solara.use_route(level=-1)
    route_current_with_children, all_routes_with_children = solara.use_route()
    router = solara.use_router()
    dark_effective = solara.lab.use_dark_effective()

    # set states for menu
    with solara.Column(gap="0px"):
        with solara.Div(classes=["news"]):
            solara.HTML(
                "div",
                unsafe_innerHTML="<a href='https://github.com/widgetti/solara' target='_blank' >Star us on github 🤩</a>",
            )
        with solara.v.AppBar(tag="header", flat=True, class_="bg-primary-fade padding-40", height="auto", clipped_left=True):
            with rv.ToolbarTitle(class_="d-flex", style_="align-items:center"):
                if route_current is not None and route_current.module is not None and hasattr(route_current.module, "Sidebar"):
                    with solara.Button(icon=True, class_="hidden-md-and-up", on_click=lambda: on_toggle_left_menu and on_toggle_left_menu()):
                        rv.Icon(children=["mdi-menu"])

            with solara.Row(
                justify="start", classes=["header-logo-container"], style={"flex-grow": "1", "background-color": "transparent", "align-items": "center"}
            ):
                with solara.Link(path_or_route="/"):
                    solara.Image(router.root_path + f"/static/assets/images/logo{'_white' if dark_effective else ''}.svg", classes=["header-logo"])

            with rv.Html(tag="ul", class_="main-menu menu d-none d-md-flex", style_="flex-grow: 1;"):
                if settings.search.enabled:
                    from solara_enterprise.search.search import Search

                    Search()
                else:
                    with solara.Row(justify="end", style={"align-items": "center", "flex-grow": "1", "background-color": "transparent"}):
                        Algolia()

                for route in all_routes:
                    if route.path in ["apps", "contact", "changelog"]:
                        continue
                    current = route_current == route
                    with rv.Html(tag="li", class_="active" if current else None):
                        solara.Link("/" + route.path if route.path != "/" else "/", children=[route.label])
            with rv.Btn(icon=True, tag="a", class_="d-none d-md-flex", attributes={"href": solara.github_url, "target": "_blank"}):
                rv.Icon(children=["mdi-github-circle"])

            with rv.Btn(icon=True, tag="a", class_="d-none d-md-flex", attributes={"href": "https://discord.solara.dev", "target": "_blank"}):
                rv.Icon(children=["mdi-discord"])

            solara.lab.ThemeToggle()

            with solara.Button(icon=True, class_="hidden-md-and-up", on_click=lambda: on_toggle_right_menu and on_toggle_right_menu()):
                rv.Icon(children=["mdi-menu"])
