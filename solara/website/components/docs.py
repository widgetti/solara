from pathlib import Path

import solara
from solara.alias import rv


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
                        with solara.Row(justify="center", gap="20px", style={"flex-wrap": "wrap", "row-gap": "20px"}):
                            for child in route.children:
                                if child.path == "/":
                                    continue
                                path = route.path + "/" + child.path
                                for extension in [".png", ".gif"]:
                                    image = path + extension
                                    image_path = Path(__file__).parent.parent / "public" / route_current.path / image
                                    image_url = "/static/public/" + route_current.path + "/" + image
                                    if image_path.exists():
                                        break
                                    else:
                                        image_url = "/static/public/logo.svg"

                                if path:
                                    path = path if route_external is None else route_current.path + "/" + path
                                    title = solara.Link(path, children=[child.label])
                                    with solara.Card(title, classes=["component-card"], margin=0):
                                        with solara.Link(path):
                                            if not image_path.exists():
                                                with solara.Column(align="center"):
                                                    solara.Image(image_url, width="120px")
                                            else:
                                                solara.Image(image_url, width="100%")


@solara.component
def NoPage():
    raise RuntimeError("This page should not be rendered")


@solara.component
def WithCode(module):
    component = getattr(module, "Page", None)
    with rv.Sheet() as main:
        # It renders code better
        solara.Markdown(
            module.__doc__ or "# no docs yet",
            unsafe_solara_execute=True,
        )
        if component and component != NoPage:
            with solara.Card("Example", margin=0, classes=["mt-8"]):
                component()
                github_url = solara.util.github_url(module.__file__)
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
        WithCode(route_current.module)
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
        with solara.Column(align="stretch", style={"width": "1024px", "flex-grow": 1}, children=children) as main:
            pass
        return main
