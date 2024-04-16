import solara


@solara.component
def Sidebar():
    route_current, all_routes = solara.use_route(-1)
    router = solara.use_router()
    if route_current is None:
        return solara.Error("Page not found")

    # Pick out documentation route, so we can use this on any page
    for route in all_routes:
        if route.path == "documentation":
            all_routes = route.children
            break

    with solara.v.List(expand=True, nav=True, style_="height: 100%; display: flex; flex-direction: column;") as main:
        with solara.v.ListItemGroup(v_model=router.path):
            for route in all_routes:
                if len(route.children) == 1 or route.path == "/":
                    with solara.Link("/documentation/" + route.path if route.path != "/" else "/documentation"):
                        with solara.v.ListItem(value="/documentation/" + route.path if route.path != "/" else "/documentation"):
                            if route.path == "/":
                                solara.v.ListItemIcon(children=[solara.v.Icon(children=["mdi-home"])])
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
                        ],
                        value=router.path.startswith("/documentation/" + route.path),
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
                                    value=router.path.startswith("/documentation/" + route.path + "/" + item.path),
                                ):
                                    for subitem in item.children:
                                        # skip pages that are only used to demonstrate Link or Router usage
                                        if subitem.path == "/" or subitem.label is None:
                                            continue
                                        path = (
                                            "/documentation/" + route.path + "/" + item.path + "/" + subitem.path
                                            if item.path != "fullscreen"
                                            else "/apps/" + subitem.path
                                        )
                                        with solara.Link(
                                            path,
                                        ):
                                            with solara.v.ListItem(dense=True, style_="padding: 0 20px;", value=path):
                                                solara.v.ListItemContent(
                                                    children=[subitem.label],
                                                )
                            else:
                                with solara.v.ListItemGroup(value="/documentation/" + route.path + "/" + item.path):
                                    with solara.Link(
                                        "/documentation/" + route.path + "/" + item.path,
                                    ):
                                        with solara.v.ListItem(dense=True, style_="padding: 0 20px;"):
                                            solara.v.ListItemContent(
                                                children=[item.label],
                                            )
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
