from typing import Callable

import solara
import solara.lab
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
    dark_effective = solara.lab.use_dark_effective()

    # set states for menu
    with solara.Column(gap="0px"):
        with solara.Div(classes=["news"]):
            solara.HTML(
                "div",
                unsafe_innerHTML="<a href='https://github.com/widgetti/solara' target='_blank' >Star us on github 🤩</a>",
            )
        with rv.AppBar(tag="header", flat=True, class_="bg-primary-fade padding-40", height="auto"):
            with rv.ToolbarTitle(class_="d-flex", style_="align-items:center"):
                if route_current and len(route_current.children) > 0:
                    with solara.Button(icon=True, class_="hidden-md-and-up", on_click=lambda: on_toggle_left_menu and on_toggle_left_menu()):
                        rv.Icon(children=["mdi-menu"])
                with solara.Link(path_or_route="/"):
                    solara.Image(router.root_path + f"/static/assets/images/logo{'_white' if dark_effective else ''}.svg")
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

            with rv.Btn(icon=True, tag="a", class_="d-none d-md-flex", attributes={"href": "https://discord.gg/dm4GKNDjXN", "target": "_blank"}):
                rv.Icon(children=["mdi-discord"])

            solara.lab.ThemeToggle()

            with solara.Button(icon=True, class_="hidden-md-and-up", on_click=lambda: on_toggle_right_menu and on_toggle_right_menu()):
                rv.Icon(children=["mdi-menu"])
