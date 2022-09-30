from pathlib import Path

import solara
from solara.alias import rv
from solara.components.title import Title
from solara.routing import route_level_context

from ..components import Header, Hero

directory = Path(__file__).parent

# md file
md = open(directory / "README.md").read()

title = "Home"

route_order = ["/", "docs", "api", "examples"]


@solara.component
def Page():
    with solara.GridFixed(1, justify_items="center") as main:
        solara.Markdown(md)
    return main


@solara.component
def SimpleListItem(text=None, children=[], class_: str = None, icon_name=None):
    if icon_name is not None:
        children = [rv.Icon(children=[icon_name])] + children
    if text is not None:
        children = [text] + children
    return rv.Html(tag="li", children=children, attributes={"class": class_})


@solara.component
def List(children=[], class_: str = None):
    return rv.Html(tag="ul", children=children, attributes={"class": class_})


@solara.component
def Sidebar():
    route_current, all_routes = solara.use_route()
    router = solara.use_router()
    selected = router.path
    with rv.Col(tag="aside", md=4, lg=3, class_="sidebar bg-grey d-none d-md-block") as main:
        with List():
            for route in all_routes:
                if route.children and route.data is None:
                    with SimpleListItem(route.label):
                        with List():
                            for child in route.children:
                                path = solara.resolve_path(child)
                                with solara.Link(path):
                                    title = child.label or "no label"
                                    if callable(title):
                                        title = "Error: dynamic title"
                                    SimpleListItem(title, class_="active" if path == selected else None)
                else:
                    path = solara.resolve_path(route)
                    with solara.Link(path):
                        SimpleListItem(route.label, class_="active" if path == selected else None)
    return main


@solara.component
def Layout(children=[]):
    router = solara.use_router()
    route_current, all_routes = solara.use_route()
    # get child routes, and restore router level, so we can also render the route of the sidebar for the mobile view
    route_level = solara.use_context(route_level_context)
    route_sidebar_current, all_routes_sidebar = solara.use_route()
    route_level_context.provide(route_level)

    show_left_menu, set_show_left_menu = solara.use_state(False)
    show_right_menu, set_show_right_menu = solara.use_state(False)

    with solara.VBox(grow=False) as main:
        Title(title="Solara documentations")
        Header(
            on_toggle_left_menu=lambda: set_show_left_menu(not show_left_menu),
            on_toggle_right_menu=lambda: set_show_right_menu(not show_right_menu),
        )
        if route_current is not None and route_current.path == "/":
            Hero(title="UI Framework for data web apps and Jupyter", button_text="Quickstart")

        with rv.Container(tag="section", fluid=True, ma_0=True, pa_0=True, class_="fill-height"):
            with rv.Row(style_="gap:6rem"):
                if route_current is not None and hasattr(route_current.module, "Sidebar"):
                    route_current.module.Sidebar()  # type: ignore
                else:
                    Sidebar()
                with rv.Col(tag="main", md=True, class_="pt-12 pl-12 pr-10", style_="max-width: 1024px"):
                    if route_current is not None and route_current.path == "/":
                        with rv.Row(align="center"):
                            pass
                            # with rv.Col(md=6, class_="pa-0"):
                            #     rv.Html(tag="h1", children=["Live Demo"])
                            # with rv.Col(md=6, class_="d-flex", style_="justify-content: end"):
                            #     rv.Btn(elevation=0, large=True, children=["Running App"], color="primary", class_="btn-size--xlarge")
                        # solara.Padding(6)
                    with rv.Row(children=children):
                        pass

            # Drawer navigation for sidebar
            with rv.NavigationDrawer(
                v_model=show_left_menu,
                on_v_model=set_show_left_menu,
                absolute=True,
                hide_overlay=False,
                overlay_color="#000000",
                overlay_opacity=0.5,
            ):
                with rv.List(nav=True):
                    with rv.ListItemGroup(active_class="text--primary"):
                        for route in all_routes:
                            with solara.Link(route):
                                solara.ListItem(route.label)

            # Drawer navigation for top menu
            with rv.NavigationDrawer(
                v_model=show_right_menu,
                on_v_model=set_show_right_menu,
                right=True,
                absolute=True,
                hide_overlay=False,
                overlay_color="#000000",
                overlay_opacity=0.5,
            ):
                with rv.List(nav=True):
                    current_path = router.path
                    with rv.ListItemGroup(active_class="text--primary", v_model=current_path):
                        for route in all_routes_sidebar:
                            # this gets rid of the api/link child routes
                            if len([k for k in route.children if k.label]) == 0:
                                with solara.Link(route):
                                    solara.ListItem(route.label, value=solara.resolve_path(route))
                            else:
                                with solara.ListItem(route.label or "no-title", value=solara.resolve_path(route) + "_no_select"):
                                    for subroute in route.children:
                                        if subroute.label:
                                            with solara.Link(subroute):
                                                with solara.ListItem(subroute.label, value=solara.resolve_path(subroute)):
                                                    pass

    return main
