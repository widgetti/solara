import contextlib

import solara
from solara.alias import rv
from solara.components.title import Title

from ..components import Header, Hero
from ..components.mailchimp import MailChimp

title = "Home"

route_order = ["/", "showcase", "docs", "api", "examples", "apps"]


@solara.component
def Page():
    solara.Markdown("should not see me")


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
                    path = getattr(route.module, "redirect", path)
                    path = getattr(route.children[0].module, "redirect", path)
                    with solara.Link(path) if path is not None else contextlib.nullcontext():
                        with SimpleListItem(route.label, class_="active" if path == selected else None):
                            with List():
                                for child in route.children[1:]:
                                    path = solara.resolve_path(child)
                                    path = getattr(child.module, "redirect", path)
                                    with solara.Link(path) if path is not None else contextlib.nullcontext():
                                        title = child.label or "no label"
                                        if callable(title):
                                            title = "Error: dynamic title"
                                        SimpleListItem(title, class_="active" if path == selected else None)
                else:
                    path = solara.resolve_path(route)
                    path = getattr(route.module, "redirect", path)
                    if route.children:
                        path = getattr(route.children[0].module, "redirect", path)
                    with solara.Link(path) if path is not None else contextlib.nullcontext():
                        SimpleListItem(route.label, class_="active" if path == selected else None)
    return main


@solara.component
def Layout(children=[]):
    router = solara.use_router()
    route_current, all_routes = solara.use_route()
    route_sidebar_current, all_routes_sidebar = solara.use_route(1)

    show_left_menu, set_show_left_menu = solara.use_state(False)
    show_right_menu, set_show_right_menu = solara.use_state(False)

    target, set_target = solara.use_state(0)

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
                title="A pure Python, React-style web framework",
                sub_title="Solara helps you build powerful & scalable Jupyter and web apps <b>faster</b> and <b>easier</b>.",
                button_text="Quickstart",
            )

        with rv.Container(tag="section", fluid=True, ma_0=True, pa_0=True, class_="fill-height mb-8 solara-content-main"):
            if route_current is not None and route_current.path == "/":
                description = "Use ipywidgets with Solara to build powerful and scalable web apps for Jupyter and production in Python."
                # both tags in one
                solara.Meta(name="description", property="og:description", content=description)
                solara.Meta(name="twitter:description", content=description)
                solara.Meta(property="og:title", content="Solara documentation")
                solara.Meta(name="twitter:title", content="Solara documentation")

                with rv.Row(class_="ma-2"):
                    with rv.Col(md=6, offset_md=3, sm=8, offset_sm=2):
                        solara.Markdown(
                            """
                        # What is Solara?

                        Solara lets you build web apps from pure Python using ipywidgets or a React-like API on
                        top of ipywidgets.
                        These apps work both inside the Jupyter Notebook and as standalone web apps with frameworks like FastAPI.

                        With Solara, you benefit from a paradigm that promotes component-based code and simplifies state management,
                        making your development process more efficient and your applications more maintainable.

                        Solara provides you with access to the full strength of the Python ecosystem.
                        This means you can continue using your favorite libraries while expanding your web development capabilities.
                        """
                        )
                        with solara.HBox():
                            with solara.Link("/docs"):
                                solara.Button(label="Read more", class_="ma-1 homepage-button", href="/docs", color="primary", dark=True)
                            with solara.Link("/docs/quickstart"):
                                solara.Button(label="Quickstart", class_="ma-1 homepage-button", color="primary", dark=True)
                    # with rv.Col(md=4, sm=5):
                    #     rv.Img(src="https://dxhl76zpt6fap.cloudfront.net/public/landing/what.webp", style_="width:900px")

                with solara.Column(style={"width": "100%"}, gap="2.5em", classes=["pt-10", "mt-8"], align="center"):
                    with solara.Row(justify="center", gap="2.5em", classes=["ma-2", "row-container"]):
                        rv.Img(src="https://dxhl76zpt6fap.cloudfront.net/public/landing/complexity.webp", contain=True)
                        solara.Markdown(
                            """
                        # Build **large** apps with **low** code complexity

                        With Solara, you can build large scale apps without hitting a complexity wall.

                        With other tools you may hit a dead end due to missing features or implementing features
                        adds too much complexity to your code base.

                        Solara offers the **flexibility** to build complex apps, but keeps the **simplicity** of a small code base.
                        """
                        )
                    with solara.Row(justify="center", gap="2.5em", classes=["ma-2", "row-container"]):
                        solara.Markdown(
                            """
                        # The trustworthiness of React

                        Using the same API as React, but ported to Python, Solara lets you build apps with the same
                        trustworthiness as React.

                        With a decade of experience, React is battle-tested and proven to be
                        a reliable and robust framework to build large scale apps.
                        """
                        )
                        with solara.Row(justify="center", style={"width": "500px"}):
                            rv.Img(src="https://dxhl76zpt6fap.cloudfront.net/public/landing/python-love-react.webp", style_="max-width:300px", contain=True)
                    with solara.Row(justify="center", gap="2.5em", classes=["ma-2", "row-container"]):
                        with solara.Column():
                            if target == 0:
                                solara.Markdown("#### Running in: Jupyter notebook")
                                solara.Image(
                                    "https://global.discourse-cdn.com/standard11/uploads/jupyter/original/2X/8/8bc875c0c3845ae077168575a4f8a49cf1b35bc6.gif"
                                )
                            else:
                                solara.Markdown("#### Running in: FastAPI")
                                solara.Image(
                                    "https://global.discourse-cdn.com/standard11/uploads/jupyter/original/2X/9/9442fc70e2a1fcd201f4f900fa073698a1f8c937.gif"
                                )
                            import solara.website.pages.apps.scatter as scatter

                            github_url = solara.util.github_url(scatter.__file__)
                            solara.Button(
                                label="View source",
                                icon_name="mdi-github-circle",
                                attributes={"href": github_url, "target": "_blank"},
                                text=True,
                                outlined=False,
                            )
                            with solara.Link("/examples"):
                                with solara.Column(style="width: 100%;"):
                                    solara.Button(
                                        label="More examples",
                                        icon_name="mdi-brain",
                                        text=True,
                                        outlined=False,
                                    )
                        with solara.Column():
                            solara.Markdown(
                                """
                                    ## Create apps

                                    In Jupyter or standalone, and run them in production
                                    using FastAPI or starlette.

                                    Get more inspiration from our [examples](/examples).
                                """
                            )
                            with rv.ExpansionPanels(v_model=target, on_v_model=set_target, mandatory=True, flat=True):
                                with rv.ExpansionPanel():
                                    rv.ExpansionPanelHeader(children=["Jupyter notebook"])
                                    with rv.ExpansionPanelContent():
                                        solara.Markdown("Build on top of ipywidgets, solara components work in all Jupyter notebook environments.")
                                with rv.ExpansionPanel():
                                    rv.ExpansionPanelHeader(children=["FastAPI"])
                                    with rv.ExpansionPanelContent():
                                        solara.Markdown(
                                            "Using [solara-server](/docs/understanding/solara-server), we can run our app in production using FastAPI."
                                        )

                with solara.Column(style={"width": "100%"}):
                    solara.v.Divider()

                with solara.Column(align="center", gap="2.5em", style={"width": "100%", "padding-bottom": "50px"}):
                    solara.Markdown("# Testimonials", style="text-align:center")
                    with solara.Row(justify="center", gap="2.5em", style={"align-items": "stretch", "flex-wrap": "wrap", "row-gap": "2.5em"}):
                        Testimonial(
                            "Solara is like streamlit, but for Jupyter. I am really excited to see where this goes!",
                            "Jack Parmer",
                            "Former CEO and Co-Founder of Plotly",
                            "https://dxhl76zpt6fap.cloudfront.net/public/avatar/jack-parmer.jpg",
                        )
                        Testimonial(
                            "Solara has been transformative, allowing us to rapidly create a Jupyter app and iterate with impressive speed.",
                            "Nick Elprin",
                            "CEO and Co-Founder of Domino Data Lab",
                            "https://dxhl76zpt6fap.cloudfront.net/public/avatar/nick-elprin.jpg",
                        )
                        Testimonial(
                            "Solara allows us to go from prototype to production with the same stack.",
                            "Jonathan Chambers",
                            "Co-founder of Planeto",
                            "https://dxhl76zpt6fap.cloudfront.net/public/avatar/jonathan-chambers.jpg",
                        )

                with solara.Column(style={"width": "100%"}):
                    solara.v.Divider()

                with solara.Column(align="center", gap="2.5em", style={"width": "100%", "padding-bottom": "50px"}):
                    solara.Markdown("# Sponsors", style="text-align:center")
                    with solara.Row(justify="center", gap="2.5em", style={"align-items": "stretch"}):
                        with solara.v.Html(tag="a", attributes={"href": "https://www.dominodatalab.com/", "target": "_blank"}):
                            solara.Image("https://dxhl76zpt6fap.cloudfront.net/public/sponsors/domino.png", width="300px")

                with solara.Column(style={"width": "100%"}):
                    solara.v.Divider()

                with solara.Row(justify="center", gap="2.5em", classes=["footer-wrapper"]):
                    with solara.Column(align="center", style={"min-width": "300px"}):
                        solara.Markdown(
                            """
                            #### For any consulting, training or support needs
                            [contact@solara.dev](mailto:contact@solara.dev)
                            """
                        )
                    solara.v.Divider(vertical=True)
                    with solara.Column(align="center", style={"min-width": "300px"}):
                        solara.Markdown("#### Join our Mailing list to get the latest news")
                        with solara.Div(style={"width": "80%"}):
                            MailChimp(location=router.path)

            else:
                with rv.Row(
                    style_="gap:6rem; flex-wrap: nowrap;", justify="center" if route_current is not None and route_current.path == "showcase" else "start"
                ):
                    if route_current is not None and hasattr(route_current.module, "Sidebar"):
                        route_current.module.Sidebar()  # type: ignore
                    else:
                        if route_current is not None and route_current.path != "showcase":
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

            # absolute = True prevents the drawer from being below the overlay it generates
            # Drawer navigation for top menu
            with rv.NavigationDrawer(
                v_model=show_right_menu,
                on_v_model=set_show_right_menu,
                fixed=True,
                absolute=True,
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
                absolute=True,
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


@solara.component
def Testimonial(text, name, position, img):
    max_width = "300px"
    with rv.Card(
        elevation=2,
        dark=False,
        max_width=max_width,
        class_="testimonial-card",
    ):
        # rv.CardTitle(children=["Former Plotly CEO"])
        with rv.CardActions():
            with rv.ListItem(class_="grow"):
                with rv.ListItemAvatar(color="grey darken-3"):
                    rv.Img(
                        class_="elevation-6",
                        src=img,
                    )
                with rv.ListItemContent():
                    rv.ListItemTitle(children=[name])
                    rv.ListItemSubtitle(children=[position], style_="white-space: unset;")
        rv.CardText(
            children=[text],
            style_="font-style: italic; padding-top: 0px",
        )
