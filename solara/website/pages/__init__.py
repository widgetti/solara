import solara
from solara import autorouting
from solara.alias import rv
from solara.components.title import Title
from solara.server import server
from solara.website.components.algolia import Algolia

from ..components import Header

title = "Home"

route_order = ["/", "showcase", "documentation", "apps", "contact", "changelog", "roadmap", "pricing", "our_team", "careers", "about", "scale_ipywidgets"]


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


@solara.component_vue("home.vue")
def Home(children=[]):
    pass


@solara.component
def Layout(children=[]):
    router = solara.use_router()
    route_current, all_routes = solara.use_route()
    route_sidebar_current, all_routes_sidebar = solara.use_route(1)

    show_left_menu, set_show_left_menu = solara.use_state(False)
    show_right_menu, set_show_right_menu = solara.use_state(False)

    target, set_target = solara.use_state(0)

    if route_current is not None:
        with solara.Head():
            solara.Meta(name="twitter:card", content="summary_large_image")
            solara.Meta(name="twitter:site", content="@solara_dev")
            solara.Meta(name="twitter:image", content="https://solara.dev/static/assets/images/logo-small.png")
            solara.Meta(property="og:url", content="https://solara.dev" + router.path)
            solara.Meta(property="og:image", content="https://solara.dev/static/assets/images/logo-small.png")
            solara.Meta(property="og:type", content="website")
    if route_current is not None and route_current.path == "apps":
        return children[0]
    elif route_current is not None and route_current.path == "/":
        Title(title="Solara: Build high-quality web applications in pure Python")
        Home()
    else:
        with solara.VBox(grow=False):
            Title(title="Solara documentation")
            Header(
                on_toggle_left_menu=lambda: set_show_left_menu(not show_left_menu),
                on_toggle_right_menu=lambda: set_show_right_menu(not show_right_menu),
            )
            with rv.Container(tag="section", fluid=True, ma_0=True, pa_0=True, class_="fill-height solara-content-main"):
                if route_current is None:
                    return solara.Error("Page not found")
                else:
                    with rv.Row(
                        style_="flex-wrap: nowrap; margin: 0; min-height: calc(100vh - 64px);",
                        justify="center" if route_current is not None and route_current.path in ["documentation", "showcase"] else "start",
                    ):
                        if route_current is not None and route_current.module is not None and hasattr(route_current.module, "Sidebar"):
                            with solara.v.Sheet(
                                style_="""
                                    height: 100vh;
                                    width: 20rem;
                                    overflow: auto;
                                    border-right: 1px solid var(--color-border-appbar);
                                    position: sticky;
                                    top: 0;
                                    flex-direction: column;
                                    gap: 0;
                                """,
                                class_="d-md-flex d-none",
                                elevation=0,
                            ):
                                route_current.module.Sidebar()
                        with rv.Col(
                            tag="main",
                            md=True,
                            class_="pa-0",
                            style_="max-width: 1024px" if route_current.path == "showcase" else "",
                        ):
                            with solara.Row(
                                children=children,
                                justify="center",
                                classes=["solara-page-content-search"],
                                style="height: unset",
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
