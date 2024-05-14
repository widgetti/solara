import solara
from solara import autorouting
from solara.alias import rv
from solara.components.title import Title
from solara.server import server
from solara.website.components.algolia import Algolia

from ..components import Header, Hero
from ..components.mailchimp import MailChimp

title = "Home"

route_order = ["/", "showcase", "documentation", "apps", "contact", "changelog"]


_redirects = {
    "/docs": "/documentation/getting_started/introduction",
    "/docs/installing": "/documentation/getting_started/installing",
    "/docs/quickstart": "/documentation/getting_started",
    "/docs/tutorial": "/documentation/getting_started/tutorials",
    "/docs/tutorial/data-science": "/documentation/getting_started/tutorials/data-science",
    "/docs/tutorial/web-app": "/documentation/getting_started/tutorials/web-app",
    "/docs/tutorial/ipywidgets": "/documentation/getting_started/tutorials/ipywidgets",
    "/docs/tutorial/streamlit": "/documentation/getting_started/tutorials/streamlit",
    "/docs/tutorial/dash": "/documentation/getting_started/tutorials/dash",
    "/docs/tutorial/jupyter-dashboard-part1": "/documentation/getting_started/tutorials/jupyter-dashboard-part1",
    "/docs/fundamentals": "/documentation/getting_started/fundamentals",
    "/docs/fundamentals/components": "/documentation/getting_started/fundamentals/components",
    "/docs/fundamentals/state-management": "/documentation/getting_started/fundamentals/state-management",
    "/docs/howto": "/documentation/advanced/howto",
    "/docs/howto/contribute": "/documentation/advanced/development/contribute",
    "/docs/howto/multipage": "/documentation/advanced/howto/multipage",
    "/docs/howto/layout": "/documentation/advanced/howto/layout",
    "/docs/howto/testing": "/documentation/advanced/howto/testing",
    "/docs/howto/debugging": "/documentation/advanced/howto/debugging",
    "/docs/howto/embed": "/documentation/advanced/howto/embed",
    "/docs/howto/ipywidget-libraries": "/documentation/advanced/howto/ipywidget-libraries",
    "/docs/reference": "/documentation/advanced/reference",
    "/docs/reference/static-files": "/documentation/advanced/reference/static-files",
    "/docs/reference/asset-files": "/documentation/advanced/reference/asset-files",
    "/docs/reference/static-site-generation": "/documentation/advanced/reference/static-site-generation",
    "/docs/reference/search": "/documentation/advanced/reference/search",
    "/docs/reference/reloading": "/documentation/advanced/reference/reloading",
    "/docs/reference/notebook-support": "/documentation/advanced/reference/notebook-support",
    "/docs/reference/caching": "/documentation/advanced/reference/caching",
    "/docs/understanding": "/documentation/advanced/understanding",
    "/docs/understanding/ipywidgets": "/documentation/advanced/understanding/ipywidgets",
    "/docs/understanding/ipyvuetify": "/documentation/advanced/understanding/ipyvuetify",
    "/docs/understanding/reacton": "/documentation/advanced/understanding/reacton",
    "/docs/understanding/reacton-basics": "/documentation/advanced/understanding/reacton-basics",
    "/docs/understanding/anatomy": "/documentation/advanced/understanding/anatomy",
    "/docs/understanding/rules-of-hooks": "/documentation/advanced/understanding/rules-of-hooks",
    "/docs/understanding/containers": "/documentation/advanced/understanding/containers",
    "/docs/understanding/solara": "/documentation/advanced/understanding/solara",
    "/docs/understanding/routing": "/documentation/advanced/understanding/routing",
    "/docs/understanding/solara-server": "/documentation/advanced/understanding/solara-server",
    "/docs/understanding/voila": "/documentation/advanced/understanding/voila",
    "/docs/deploying": "/documentation/getting_started/deploying",
    "/docs/deploying/self-hosted": "/documentation/getting_started/deploying/self-hosted",
    "/docs/deploying/cloud-hosted": "/documentation/getting_started/deploying/cloud-hosted",
    "/docs/enterprise": "/documentation/advanced/enterprise",
    "/docs/enterprise/oauth": "/documentation/advanced/enterprise/oauth",
    "/docs/development": "/documentation/advanced/development/setup",
    "/docs/troubleshoot": "/documentation/getting_started/troubleshoot",
    "/docs/changelog": "/changelog",
    "/docs/contact": "/contact",
    "/docs/faq": "/documentation/faq",
    "/docs/lab": "/documentation/getting_started/what-is-lab",
    "/api": "/documentation/api",
    "/api/altair": "/documentation/components/viz/altair",
    "/api/app_bar": "/documentation/components/layout/app_bar",
    "/api/app_bar_title": "/documentation/components/layout/app_bar_title",
    "/api/app_layout": "/documentation/components/layout/app_layout",
    "/api/avatar": "/documentation/components/enterprise/avatar",
    "/api/avatar_menu": "/documentation/components/enterprise/avatar_menu",
    "/api/card": "/documentation/components/layout/card",
    "/api/card_actions": "/documentation/components/layout/card_actions",
    "/api/column": "/documentation/components/layout/column",
    "/api/columns": "/documentation/components/layout/columns",
    "/api/columns_responsive": "/documentation/components/layout/columns_responsive",
    "/api/cross_filter_dataframe": "/documentation/api/cross_filter/cross_filter_dataframe",
    "/api/cross_filter_report": "/documentation/api/cross_filter/cross_filter_report",
    "/api/cross_filter_select": "/documentation/api/cross_filter/cross_filter_select",
    "/api/cross_filter_slider": "/documentation/api/cross_filter/cross_filter_slider",
    "/api/generate_routes": "/documentation/api/routing/generate_routes",
    "/api/generate_routes_directory": "/documentation/api/routing/generate_routes_directory",
    "/api/resolve_path": "/documentation/api/routing/resolve_path",
    "/api/resolve_path/kiwi": "/documentation/api/routing/resolve_path/kiwi",
    "/api/resolve_path/banana": "/documentation/api/routing/resolve_path/banana",
    "/api/resolve_path/apple": "/documentation/api/routing/resolve_path/apple",
    "/api/link": "/documentation/components/advanced/link",
    "/api/link/kiwi": "/documentation/components/advanced/link/kiwi",
    "/api/link/banana": "/documentation/components/advanced/link/banana",
    "/api/link/apple": "/documentation/components/advanced/link/apple",
    "/api/use_route": "/documentation/api/routing/use_route",
    "/api/use_route/fruit": "/documentation/api/routing/use_route/fruit",
    "/api/use_route/fruit/kiwi": "/documentation/api/routing/use_route/fruit/kiwi",
    "/api/use_route/fruit/banana": "/documentation/api/routing/use_route/fruit/banana",
    "/api/use_route/fruit/apple": "/documentation/api/routing/use_route/fruit/apple",
    "/api/use_router": "/documentation/api/routing/use_router",
    "/api/use_cross_filter": "/documentation/api/hooks/use_cross_filter",
    "/api/use_dark_effective": "/documentation/api/hooks/use_dark_effective",
    "/api/use_effect": "/documentation/api/hooks/use_effect",
    "/api/use_exception": "/documentation/api/hooks/use_exception",
    "/api/use_memo": "/documentation/api/hooks/use_memo",
    "/api/use_previous": "/documentation/api/hooks/use_previous",
    "/api/use_reactive": "/documentation/api/hooks/use_reactive",
    "/api/use_state": "/documentation/api/hooks/use_state",
    "/api/use_state_or_update": "/documentation/api/hooks/use_state_or_update",
    "/api/use_task": "/documentation/components/lab/use_task",
    "/api/use_thread": "/documentation/api/hooks/use_thread",
    "/api/use_trait_observe": "/documentation/api/hooks/use_trait_observe",
    "/examples/fullscreen": "/documentation/examples/fullscreen",
    "/examples/fullscreen/authorization": "/apps/authorization",
    "documentation/examples/fullscreen/authorization": "/apps/authorization",
    "/examples/fullscreen/layout-demo": "/apps/layout-demo",
    "/documentation/examples/fullscreen/layout_demo": "/apps/layout-demo",
    "/examples/fullscreen/multipage": "/apps/multipage",
    "/documentation/examples/fullscreen/multipage": "/apps/multipage",
    "/examples/fullscreen/scatter": "apps/scatter",
    "/documentation/examples/fullscreen/scatter": "/apps/scatter",
    "/examples/fullscreen/scrolling": "/apps/scrolling",
    "/documentation/examples/fullscreen/scrolling": "/apps/scrolling",
    "/examples/fullscreen/tutorial-streamlit": "/apps/tutorial-streamlit",
    "/documentation/examples/fullscreen/tutorial_streamlit": "/apps/tutorial-streamlit",
    "/api/route": "/documentation/api/routing/route",
    "/api/route/kiwi": "/documentation/api/routing/route/kiwi",
    "/api/route/banana": "/documentation/api/routing/route/banana",
    "/api/route/apple": "/documentation/api/routing/route/apple",
    "/examples/libraries": "/documentation/examples/libraries",
    "/examples/libraries/altair": "/documentation/examples/libraries/altair",
    "/examples/libraries/bqplot": "/documentation/examples/libraries/bqplot",
    "/examples/libraries/ipyleaflet": "/documentation/examples/libraries/ipyleaflet",
    "/examples/libraries/ipyleaflet_advanced": "/documentation/examples/libraries/ipyleaflet_advanced",
    "/examples/utilities": "/documentation/examples/utilities",
    "/examples/utilities/calculator": "/documentation/examples/utilities/calculator",
    "/examples/utilities/countdown_timer": "/documentation/examples/utilities/countdown_timer",
    "/examples/utilities/todo": "/documentation/examples/utilities/todo",
    "/examples/visualization": "/documentation/examples/visualization",
    "/examples/visualization/annotator": "/documentation/examples/visualization/annotator",
    "/examples/visualization/linked_views": "/documentation/examples/visualization/linked_views",
    "/examples/visualization/plotly": "/documentation/examples/visualization/plotly",
    "/examples/general": "/documentation/examples/general",
    "/examples/general/custom_storage": "/documentation/examples/general/custom_storage",
    "/examples/general/deploy_model": "/documentation/examples/general/deploy_model",
    "/examples/general/live_update": "/documentation/examples/general/live_update",
    "/examples/general/login_oauth": "/documentation/examples/general/login_oauth",
    "/examples/general/pokemon_search": "/documentation/examples/general/pokemon_search",
    "/examples/general/vue_component": "/documentation/examples/general/vue_component",
    "/examples": "/documentation/examples",
    "/examples/ai": "/documentation/examples/ai",
    "/examples/ai/chatbot": "/documentation/examples/ai/chatbot",
    "/examples/ai/tokenizer": "/documentation/examples/ai/tokenizer",
    "/examples/basics": "/documentation/examples/basics",
    "/examples/basics/sine": "/documentation/examples/basics/sine",
    "/api/get_kernel_id": "/documentation/api/utilities/get_kernel_id",
    "/api/get_session_id": "/documentation/api/utilities/get_session_id",
    "/api/on_kernel_start": "/documentation/api/utilities/on_kernel_start",
    "/api/component_vue": "/documentation/api/utilities/component_vue",
    "/api/plotly": "/documentation/components/viz/plotly",
    "/api/plotly_express": "/documentation/components/viz/plotly_express",
    "/api/tab": "/documentation/components/lab/tab",
    "/api/tabs": "/documentation/components/lab/tabs",
    "/api/task": "/documentation/components/lab/task",
    "/api/computed": "/documentation/api/utilities/computed",
    "/api/markdown": "/documentation/components/output/markdown",
    "/api/markdown_editor": "/documentation/components/output/markdown_editor",
    "/api/matplotlib": "/documentation/components/viz/matplotlib",
    "/api/echarts": "/documentation/components/viz/echarts",
    "/api/theming": "/documentation/components/lab/theming",
    "/api/griddraggable": "/documentation/components/layout/griddraggable",
    "/api/gridfixed": "/documentation/components/layout/gridfixed",
    "/api/html": "/documentation/components/output/html",
    "/api/file_download": "/documentation/components/output/file_download",
    "/api/hbox": "/documentation/components/layout/hbox",
    "/api/vbox": "/documentation/components/layout/vbox",
    "/api/sidebar": "/documentation/components/layout/sidebar",
    "/api/row": "/documentation/components/layout/row",
    "/api/error": "/documentation/components/status/error",
    "/api/info": "/documentation/components/status/info",
    "/api/progress": "/documentation/components/status/progress",
    "/api/spinner": "/documentation/components/status/spinner",
    "/api/success": "/documentation/components/status/success",
    "/api/warning": "/documentation/components/status/warning",
    "/api/image": "/documentation/components/output/image",
    "/api/sql_code": "/documentation/components/output/sql_code",
    "/api/tooltip": "/documentation/components/output/tooltip",
    "/api/chat": "/documentation/components/lab/chat",
    "/api/confirmation_dialog": "/documentation/components/lab/confirmation_dialog",
    "/api/cookies_headers": "/documentation/components/lab/cookies_headers",
    "/api/input_date": "/documentation/components/lab/input_date",
    "/api/button": "/documentation/components/input/button",
    "/api/checkbox": "/documentation/components/input/checkbox",
    "/api/file_browser": "/documentation/components/input/file_browser",
    "/api/file_drop": "/documentation/components/input/file_drop",
    "/api/meta": "/documentation/components/advanced/meta",
    "/api/style": "/documentation/components/advanced/style",
    "/api/menu": "/documentation/components/lab/menu",
    "/api/head": "/documentation/components/page/head",
    "/api/input": "/documentation/components/input/input",
    "/api/select": "/documentation/components/input/select",
    "/api/slider": "/documentation/components/input/slider",
    "/api/switch": "/documentation/components/input/switch",
    "/api/togglebuttons": "/documentation/components/input/togglebuttons",
    "/api/dataframe": "/documentation/components/data/dataframe",
    "/api/pivot_table": "/documentation/components/data/pivot_table",
    "/api/display": "/documentation/api/utilities/display",
    "/api/memoize": "/documentation/api/utilities/memoize",
    "/api/reactive": "/documentation/api/utilities/reactive",
    "/api/widget": "/documentation/api/utilities/widget",
    "/api/default_layout": "/documentation/components/layout",
    "/api/title": "/documentation/components/page/title",
}


server._redirects = _redirects
autorouting._redirects = _redirects


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

        with rv.Container(tag="section", fluid=True, ma_0=True, pa_0=True, class_="fill-height solara-content-main"):
            if route_current is None:
                return solara.Error("Page not found")
            elif route_current.path == "/":
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
                            with solara.Link("/documentation"):
                                solara.Button(label="Read more", class_="ma-1 homepage-button", href="/documentation", color="primary", dark=True)
                            with solara.Link("/documentation/getting_started"):
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
                            with solara.Link("/documentation/examples"):
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

                                    Get more inspiration from our [examples](/documentation/examples).
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
                                            """Using [solara-server](documentation/advanced/understanding/solara-server),
                                            we can run our app in production using FastAPI."""
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
                    style_="flex-wrap: nowrap; margin: 0; min-height: calc(100vh - 215.5px);",
                    justify="center" if route_current is not None and route_current.path in ["documentation", "showcase"] else "start",
                ):
                    if route_current is not None and route_current.module is not None and hasattr(route_current.module, "Sidebar"):
                        with solara.v.NavigationDrawer(
                            clipped=True,
                            class_="d-none d-md-block",
                            height="unset",
                            style_="min-height: calc(100vh - 215.5px);",
                            width="20rem",
                            v_model=True,  # Forces menu to display even if it had somehow been closed
                        ):
                            route_current.module.Sidebar()
                    with rv.Col(
                        tag="main",
                        md=True,
                        class_="pa-0",
                        style_=f"""max-width: {'1024px' if route_current.path not in ['documentation', 'contact', 'changelog']
                                               else 'unset'}; overflow-x: hidden;""",
                    ):
                        if route_current is not None and route_current.path == "/":
                            with rv.Row(align="center"):
                                pass
                        with solara.Row(
                            children=children,
                            justify="center",
                            classes=["solara-page-content-search"],
                            style=f"height: {'100%' if route_current.path == 'documentation' else 'unset'};",
                        ):
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
                Algolia()
                with rv.List(nav=True):
                    with rv.ListItemGroup(active_class="text--primary"):
                        for route in all_routes:
                            if route.path == "apps":
                                continue
                            with solara.Link(route):
                                solara.ListItem(route.label)

            if route_current is not None and route_current.module is not None and hasattr(route_current.module, "Sidebar"):
                with solara.v.NavigationDrawer(
                    absolute=True,
                    clipped=True,
                    class_="d-md-none d-block",
                    height="unset",
                    style_="min-height: 100vh;",
                    v_model=show_left_menu,
                    on_v_model=set_show_left_menu,
                    width="20rem",
                ):
                    route_current.module.Sidebar()

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
