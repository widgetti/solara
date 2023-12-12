from pathlib import Path

import solara
from solara.alias import rv

from ..api import NoPage, WithCode  # noqa

items = [
    {
        "name": "Input",
        "icon": "mdi-chevron-left-box",
        "pages": ["button", "checkbox", "input", "select", "slider", "switch", "togglebuttons", "file_browser", "file_drop"],
    },
    {
        "name": "Output",
        "icon": "mdi-chevron-right-box",
        "pages": ["markdown", "markdown_editor", "html", "image", "sql_code", "file_download", "tooltip"],
    },
    {
        "name": "Status",
        "icon": "mdi-information",
        "pages": ["success", "info", "warning", "error", "spinner", "progress"],
    },
    {
        "name": "Viz",
        "icon": "mdi-chart-histogram",
        "pages": ["altair", "echarts", "matplotlib", "plotly", "plotly_express"],
    },
    {
        "name": "Layout",
        "icon": "mdi-page-layout-sidebar-left",
        "pages": [
            "app_layout",
            "app_bar",
            "app_bar_title",
            "card",
            "card_actions",
            "columns",
            "columns_responsive",
            "column",
            "row",
            "griddraggable",
            "gridfixed",
            "sidebar",
            "hbox",
            "vbox",
        ],
    },
    {
        "name": "Data",
        "icon": "mdi-database",
        "pages": ["dataframe", "pivot_table"],
    },
    {
        "name": "Page",
        "icon": "mdi-file-code",
        "pages": ["head", "title"],
    },
    {
        "name": "Advanced",
        "icon": "mdi-head-cog-outline",
        "pages": ["style", "meta"],
    },
    {
        "name": "Enterprise",
        "icon": "mdi-office-building",
        "pages": ["avatar", "avatar_menu"],
    },
    {
        "name": "Lab (experimental)",
        "icon": "mdi-flask-outline",
        "pages": [
            "computed",
            "chat",
            "confirmation_dialog",
            "cookies_headers",
            "menu",
            "input_date",
            "on_kernel_start",
            "tab",
            "tabs",
            "task",
            "use_task",
        ],
    },
]


@solara.component
def Page(route_external=None):
    if route_external is not None:
        route_current = route_external
    else:
        # show a gallery of all the api pages
        router = solara.use_router()
        route_current = router.path_routes[-2]

    routes = {r.path: r for r in route_current.children}
    for item in items:
        solara.Markdown(f"## {item['name']}")
        with solara.Row(justify="center", gap="20px", style={"flex-wrap": "wrap", "row-gap": "20px"}):
            for page in item["pages"]:
                if page not in routes:
                    continue
                route = routes[page]
                path = route.path
                image_path = None
                image_url = None
                for suffix in [".png", ".gif"]:
                    image = path + suffix
                    image_path = Path(__file__).parent.parent.parent.parent / "public" / "api" / image
                    image_url = "/static/public/api/" + image
                    if image_path.exists():
                        break
                assert image_path is not None
                assert image_url is not None
                if not image_path.exists():
                    image_url = "/static/public/logo.svg"

                path = getattr(route.module, "redirect", path)
                if path:
                    with solara.Card(classes=["component-card"], margin=0):
                        rv.CardTitle(children=[solara.Link(path if route_external is None else "components/" + path, children=[route.label])])
                        with rv.CardText():
                            with solara.Link(path if route_external is None else "components/" + path):
                                if not image_path.exists():
                                    pass
                                    with solara.Column(align="center"):
                                        solara.Image(image_url, width="120px")
                                else:
                                    solara.Image(image_url, width="100%")
                        doc = route.module.__doc__ or ""
                        if doc:
                            lines = doc.split("\n")
                            lines = [line.strip() for line in lines if line.strip()]
                            first = lines[1]

                            rv.CardText(
                                children=[solara.Markdown(first)],
                            )


@solara.component
def Layout(children=[]):
    route_current, all_routes = solara.use_route()
    if route_current is None:
        return solara.Error("Page not found")

    if route_current.path == "/":
        return Page()
    else:
        with solara.Column(align="center") as main:
            with solara.Column(align="center", style={"max-width": "1024px"}):
                if route_current.module:
                    # we ignore children, and make the element again
                    WithCode(route_current.module)
        return main
