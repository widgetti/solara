from pathlib import Path

import solara
from solara.server import settings

_title = "Documentation"

HERE = Path(__file__).parent


@solara.component_vue(str(HERE.parent.parent) + "/components/algolia_api.vue")
def Algolia():
    pass


@solara.component
def Page(children=[]):
    # show a gallery of all the api pages
    router = solara.use_router()
    route_current = router.path_routes[-2]

    with solara.Column(style={"width": "100%"}, classes=["pr-md-10"]):
        with solara.Column(
            classes=["api-search-container"] if route_current.path == "documentation" else [], gap="75px", style={"justify-content": "center"}, align="center"
        ):
            solara.Markdown("# Search the Solara Documentation", style={"text-align": "center"})

            if settings.search.enabled:
                from solara_enterprise.search.search import Search

                query = solara.use_reactive("")
                input = solara.v.TextField(
                    v_model=query.value,
                    on_v_model=query.set,
                    background_color="#ffeec5",
                    outlined=True,
                    label="Search",
                    class_="api-search",
                    rounded=True,
                    prepend_inner_icon="mdi-magnify",
                    style_="min-width: 19rem; width: 33%;",
                    hide_details=True,
                )

                Search(input_widget=input, query=query.value)
            else:
                Algolia()

        if route_current.path == "documentation":
            QuickBrowse(route_current)
        else:
            with solara.Row(justify="center", style={"align-items": "start"}, children=children):
                pass


@solara.component
def QuickBrowse(route_current):
    selected = solara.use_reactive("")

    with solara.Column(gap="75px", align="center"):
        with solara.Row(justify="center", gap="30px", style={"flex-wrap": "wrap", "align-items": "start", "row-gap": "30px"}):
            for child in reversed(route_current.children):
                if child.path == "/":
                    continue
                solara.Button(
                    child.label,
                    on_click=lambda path=child.path: selected.set(path),
                    color="primary",
                    classes=["v-btn--rounded", "v-size--x-large", "darken-3" if selected.value == child.path else ""],
                )
        if selected.value:
            with solara.v.TabsItems(v_model=selected.value, style_=f"width: {'1024px' if selected.value in ['getting_started', 'faq'] else '90%'};"):
                for child in reversed(route_current.children):
                    if child.path == "/":
                        continue
                    with solara.v.TabItem(v_model=child.path, style={"width": "100%"}):
                        with solara.Column(style={"flex-grow": "1"}):
                            with solara.Link("/" + route_current.path + "/" + child.path if child.path != "/" else "/" + route_current.path):
                                solara.HTML(tag="h2", unsafe_innerHTML=child.label, style={"text-align": "center"})
                            child.module.Page(route_external=child)


@solara.component
def Sidebar():
    route_current, all_routes = solara.use_route()
    if route_current is None:
        return solara.Error("Page not found")

    with solara.v.NavigationDrawer(clipped=True, height="unset", style_="min-height: calc(100vh - 215.5px);", class_="d-none d-md-block") as main:
        with solara.v.List(expand=True, nav=True, style_="height: calc(100vh - 215.5px); display: flex; flex-direction: column;"):
            with solara.v.ListItemGroup():
                with solara.Link("/documentation/"):
                    with solara.v.ListItem():
                        solara.v.ListItemIcon(children=[solara.v.Icon(children=["mdi-home"])])
                        solara.v.ListItemTitle(style_="padding: 0 20px;", children=["Home"])
            for route in reversed(all_routes):
                if route.path == "/":
                    continue
                if len(route.children) == 1:
                    with solara.v.ListItemGroup():
                        with solara.Link("/documentation/" + route.path):
                            with solara.v.ListItem():
                                solara.v.ListItemTitle(style_="padding: 0 20px;", children=[route.label])
                else:
                    with solara.v.ListGroup(
                        v_slots=[
                            {
                                "name": "activator",
                                "children": solara.v.ListItemTitle(
                                    children=[route.label],
                                    style_="padding: 0 20px;",
                                ),
                            }
                        ]
                    ):
                        for item in route.children:
                            if item.path == "/":
                                continue
                            if item.children != [] and any([c.label is not None and c.path != "/" for c in item.children]):
                                with solara.v.ListGroup(
                                    v_slots=[
                                        {
                                            "name": "activator",
                                            "children": solara.v.ListItemTitle(
                                                children=[item.label],
                                            ),
                                        }
                                    ],
                                    sub_group=True,
                                    no_action=True,
                                ):
                                    for subitem in item.children:
                                        # skip pages that are only used to demonstrate Link or Router usage
                                        if subitem.path == "/" or subitem.label is None:
                                            continue
                                        with solara.v.ListItemGroup():
                                            with solara.Link(
                                                "/documentation/" + route.path + "/" + item.path + "/" + subitem.path,
                                            ):
                                                with solara.v.ListItem(dense=True, style_="padding: 0 20px;"):
                                                    solara.v.ListItemContent(
                                                        children=[subitem.label],
                                                    )
                            else:
                                with solara.v.ListItemGroup():
                                    with solara.Link(
                                        "/documentation/" + route.path + "/" + item.path,
                                    ):
                                        with solara.v.ListItem(dense=True, style_="padding: 0 20px;"):
                                            solara.v.ListItemContent(
                                                children=[item.label],
                                            )
            solara.v.Spacer(style_="flex-grow: 1;")
            with solara.v.ListItemGroup():
                with solara.Link("/contact"):
                    with solara.v.ListItem():
                        solara.v.ListItemIcon(children=[solara.v.Icon(children=["mdi-email"])])
                        solara.v.ListItemTitle(style_="padding: 0 20px;", children=["Contact"])
                with solara.Link("/changelog"):
                    with solara.v.ListItem():
                        solara.v.ListItemIcon(children=[solara.v.Icon(children=["mdi-history"])])
                        solara.v.ListItemTitle(style_="padding: 0 20px;", children=["Changelog"])

    return main


@solara.component
def WithCode(module):
    # e = solara.use_exception_handler()
    # if e is not None:
    #     return solara.Error("oops")
    component = getattr(module, "Page", None)
    with solara.Column() as main:
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
def Layout(children=[]):
    route_current, all_routes = solara.use_route()
    if route_current is None:
        return solara.Error("Page not found")

    if route_current.path == "/":
        return Page()
    else:
        return Page(children=children)


@solara.component
def NoPage():
    raise RuntimeError("This page should not be rendered")
