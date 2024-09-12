import solara
from .markdown import MarkdownWithMetadata
from .breadcrumbs import BreadCrumbs


@solara.component
def Gallery(route_external=None):
    if route_external is not None:
        route_current = route_external
    else:
        # show a gallery of all the examples
        router = solara.use_router()
        route_current = router.path_routes[-2]

    with solara.Column(gap="75px", align="center"):
        with solara.Row(justify="center", gap="30px", style={"margin": "30px 0 !important", "flex-wrap": "wrap", "align-items": "start", "row-gap": "30px"}):
            for child in route_current.children:
                if child.path == "/":
                    continue
                with solara.v.Html(tag="a", attributes={"href": "#" + child.path}):
                    solara.Button(
                        child.label,
                        color="primary",
                        classes=["v-btn--rounded", "v-size--x-large"],
                    )

        with solara.Column(gap="75px", style={"padding-bottom": "75px"}):
            for route in route_current.children:
                if route.children:
                    with solara.Column(classes=["subcategory-row", "ps-md-10"]):
                        solara.HTML(tag="h2", unsafe_innerHTML=route.label, attributes={"id": route.path}, style="padding-left: 10%;")
                        with solara.Row(justify="center", gap="20px", style={"flex-wrap": "wrap", "row-gap": "20px", "max-width": "90rem"}):
                            for child in route.children:
                                if child.path == "/":
                                    continue
                                path = route.path + "/" + child.path
                                if child.path in [
                                    "button",
                                    "checkbox",
                                    "confirmation_dialog",
                                    "echarts",
                                    "file_browser",
                                    "file_download",
                                    "matplotlib",
                                    "select",
                                    "switch",
                                    "tooltip",
                                ]:
                                    image_url = "https://dxhl76zpt6fap.cloudfront.net/public/api/" + child.path + ".gif"
                                elif child.path in ["card", "dataframe", "pivot_table", "slider"]:
                                    image_url = "https://dxhl76zpt6fap.cloudfront.net/public/api/" + child.path + ".png"
                                else:
                                    image_url = "https://dxhl76zpt6fap.cloudfront.net/public/logo.svg"

                                if path:
                                    path = path if route_external is None else route_current.path + "/" + path
                                    title = solara.Link(path, children=[child.label])
                                    with solara.Card(title, classes=["component-card"], margin=0):
                                        with solara.Column(align="center"):
                                            with solara.Link(path):
                                                solara.Image(image_url, width="12rem")


@solara.component
def NoPage():
    raise RuntimeError("This page should not be rendered")


@solara.component
def WithCode(route_current):
    component = getattr(route_current.module, "Page", None)
    with solara.Column(style={"flex-grow": 1, "padding-top": "56px"}) as main:
        BreadCrumbs()
        # It renders code better
        MarkdownWithMetadata(
            route_current.module.__doc__ or "# no docs yet",
            unsafe_solara_execute=True,
        )
        if component and component != NoPage:
            with solara.Card("Example", margin=0, classes=["mt-8"]):
                component()
                github_url = solara.util.github_url(route_current.module.__file__)
                solara.Button(
                    label="View source",
                    icon_name="mdi-github-circle",
                    attributes={"href": github_url, "target": "_blank"},
                    text=True,
                    outlined=True,
                    class_="mt-8",
                )
    return main


@solara.component
def SubCategoryLayout(children=[]):
    route_current, all_routes = solara.use_route()
    if route_current is None:
        return solara.Error("Page not found")
    elif route_current.path == "/":
        return solara.Error("Not supposed to be rendered")
    elif route_current.module:
        WithCode(route_current)
    else:
        with solara.Column(align="center", children=children, style={"flex-grow": 1, "padding": "0"}) as main:
            pass
        return main


@solara.component
def CategoryLayout(children=[]):
    route_current, all_routes = solara.use_route()
    if route_current is None:
        return solara.Error("Page not found")

    if route_current.path == "/":
        return Gallery()
    else:
        with solara.Column(align="stretch", children=children, style={"max-width": "100%"}) as main:
            pass
        return main
