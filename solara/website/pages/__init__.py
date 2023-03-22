from pathlib import Path

import solara
from solara.alias import rv
from solara.components.title import Title

from ..components import Header, Hero

directory = Path(__file__).parent

# md file
md = open(directory / "README.md").read()

title = "Home"

route_order = ["/", "docs", "api", "examples", "apps"]


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
                    path = solara.resolve_path(route.children[0])
                    with solara.Link(path):
                        with SimpleListItem(route.label, class_="active" if path == selected else None):
                            with List():
                                for child in route.children[1:]:
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
    route_sidebar_current, all_routes_sidebar = solara.use_route(1)

    show_left_menu, set_show_left_menu = solara.use_state(False)
    show_right_menu, set_show_right_menu = solara.use_state(False)

    if route_current and route_current.path == "apps":
        return children[0]
    with solara.VBox(grow=False) as main:
        Title(title="Solara documentation")
        solara.Meta(name="twitter:card", content="summary_large_image")
        solara.Meta(name="twitter:site", content="@solara_dev")
        solara.Meta(name="twitter:image", content="https://solara.dev/static/assets/images/logo-small.png")
        solara.Meta(property="og:url", content="https://solara.dev" + router.path)
        solara.Meta(property="og:image", content="https://solara.dev/static/assets/images/logo-small.png")
        solara.Meta(property="og:type", content="website")
        Header(
            on_toggle_left_menu=lambda: set_show_left_menu(not show_left_menu),
            on_toggle_right_menu=lambda: set_show_right_menu(not show_right_menu),
        )
        if route_current is not None and route_current.path == "/":
            Hero(
                title="Build large and Scalable Web Apps for Jupyter and Production",
                sub_title="Solara helps you build powerful & scalable data apps <b>faster</b> and <b>easier</b>.",
                button_text="Quickstart",
            )

        with rv.Container(tag="section", fluid=True, ma_0=True, pa_0=True, class_="fill-height mb-8"):
            if route_current is not None and route_current.path == "/":
                description = "Use ipywidgets with Solara to build powerful and scalable web apps for Jupyter and production in Python."
                # both tags in one
                solara.Meta(name="description", property="og:description", content=description)
                solara.Meta(name="twitter:description", content=description)
                solara.Meta(property="og:title", content="Solara documentation")
                solara.Meta(name="twitter:title", content="Solara documentation")

                with rv.Row(class_="ma-2"):
                    with rv.Col(md=4, offset_md=2, sm=5, offset_sm=1):
                        solara.Markdown(
                            """
                        # What is Solara?

                        Solara lets you build web apps from pure Python using ipywidgets.

                        Grow from a one-off experiment in the Jupyter notebook to highly complex production-grade web apps with confidence.

                        Access the full power of the Python ecosystem. Use your favorite libraries.
                        """
                        )
                        with solara.HBox():
                            with solara.Link("/docs"):
                                solara.Button(label="Read more", class_="ma-1", href="/docs", color="#f19f41", dark=True)
                            with solara.Link("/docs/quickstart"):
                                solara.Button(label="Quickstart", class_="ma-1", color="#f19f41", dark=True)
                    with rv.Col(md=4, sm=5):
                        rv.Img(src="/static/public/landing/what.png", style_="width:900px")

                with rv.Row(class_="ma-8"):
                    with rv.Col(md=4, offset_md=2, sm=5, offset_sm=1):
                        rv.Img(src="/static/public/landing/complexity.png", style_="width:500px")
                    with rv.Col(md=4, sm=5):
                        solara.Markdown(
                            """
                        # Build **large** apps with **low** code complexity

                        With Solara, you can build large scale apps without hitting a complexity wall.

                        With other tools you may hit a dead end due to missing features or implementing features
                        adds too much complexity to your code base.

                        Solara offers the **flexibility** to build complex apps, but keeps the **simplicity** of a small code base.
                        """
                        )
                with rv.Row(class_="ma-8"):
                    with rv.Col(md=4, sm=5, offset_sm=1, offset_md=2):
                        solara.Markdown(
                            """
                        # The trustworthiness of React

                        Using the same API as React, but ported to Python, Solara lets you build apps with the same
                        trustworthiness as React.

                        With a decade of experience, React is battle-tested and proven to be
                        a reliable and robust framework to build large scale apps.
                        """
                        )
                    with rv.Col(md=5, sm=5):
                        rv.Img(src="/static/public/landing/python-love-react.png", style_="width:300px")
                with rv.Row(class_="ma-8"):
                    with rv.Col(md=5, offset_md=2, sm=5, offset_sm=1):
                        solara.Markdown(
                            """
                        ## For any consulting, training or support needs
                        [contact@solara.dev](mailto:contact@solara.dev)
                        """
                        )
            else:
                with rv.Row(style_="gap:6rem; flex-wrap: nowrap;"):
                    if route_current is not None and hasattr(route_current.module, "Sidebar"):
                        route_current.module.Sidebar()  # type: ignore
                    else:
                        Sidebar()
                    with rv.Col(tag="main", md=True, class_="pt-12 pl-12 pr-10", style_="max-width: 1024px; overflow: auto;"):
                        if route_current is not None and route_current.path == "/":
                            with rv.Row(align="center"):
                                pass
                                # with rv.Col(md=6, class_="pa-0"):
                                #     rv.Html(tag="h1", children=["Live Demo"])
                                # with rv.Col(md=6, class_="d-flex", style_="justify-content: end"):
                                #     rv.Btn(elevation=0, large=True, children=["Running App"], color="primary", class_="btn-size--xlarge")
                            # solara.Padding(6)
                        with rv.Row(children=children, class_="solara-page-content-search"):
                            pass

            # Drawer navigation for top menu
            with rv.NavigationDrawer(
                v_model=show_right_menu,
                on_v_model=set_show_right_menu,
                fixed=True,
                right=True,
                hide_overlay=False,
                overlay_color="#000000",
                overlay_opacity=0.5,
                style_="height: 100vh",
            ):
                with rv.List(nav=True):
                    with rv.ListItemGroup(active_class="text--primary"):
                        for route in all_routes:
                            if route.path == "apps":
                                continue
                            with solara.Link(route):
                                solara.ListItem(route.label)

            # Drawer navigation for sidebar
            with rv.NavigationDrawer(
                v_model=show_left_menu,
                on_v_model=set_show_left_menu,
                fixed=True,
                hide_overlay=False,
                overlay_color="#000000",
                overlay_opacity=0.5,
                style_="height: 100vh",
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
