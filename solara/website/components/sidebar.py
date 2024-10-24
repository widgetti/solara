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

    with solara.v.List(
        expand=True,
        nav=True,
        style_="height: 100%; max-height: 100vh; display: flex; flex-direction: column; background-color: var(--color-material-background); overflow-y: auto;",
    ) as main:
        with solara.v.ListItemGroup(v_model=router.path):
            # e.g. getting_started, examples, components, api, advanced, faq
            for route in all_routes:
                if len(route.children) == 1 or route.path == "/":
                    with solara.Link("/documentation/" + route.path if route.path != "/" else "/documentation"):
                        with solara.v.ListItem(value="/documentation/" + route.path if route.path != "/" else "/documentation"):
                            if route.path == "/":
                                solara.v.ListItemIcon(children=[solara.v.Icon(children=["mdi-home"])])
                            solara.v.ListItemTitle(style_="padding: 0 20px;", children=[route.label])
                else:
                    path_top_level = "/documentation/" + route.path
                    top_level_expanded = router.path.startswith(path_top_level)
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
                        value=top_level_expanded,
                        eager=True,  # better for SEO
                    ):
                        for item in route.children:
                            label = item.label
                            if item.path == "/" and route.path in ["examples", "api", "components"]:
                                # the 'homepage' of the subpage are named Overview
                                label = "Overview"
                            path_sub = "/documentation/" + route.path + "/" + item.path
                            sub_should_be_expanded = router.path.startswith(path_sub)
                            if item.children != [] and any([c.label is not None and c.path != "/" for c in item.children]):
                                with solara.v.ListGroup(
                                    v_slots=[
                                        {
                                            "name": "activator",
                                            "children": solara.v.ListItemTitle(
                                                children=[label],
                                            ),
                                        }
                                    ],
                                    sub_group=True,
                                    no_action=True,
                                    eager=True,  # better for SEO
                                    value=sub_should_be_expanded,
                                ):
                                    for subitem in item.children:
                                        # skip the 'homepage' of the examples only
                                        if subitem.path == "/" and route.path not in ["getting_started", "advanced"]:
                                            continue
                                        path = (
                                            "/documentation/" + route.path + "/" + item.path + "/" + (subitem.path if subitem.path != "/" else "")
                                            if item.path != "fullscreen"
                                            else "/apps/" + subitem.path
                                        )
                                        with solara.Link(
                                            path,
                                        ):
                                            with solara.v.ListItem(dense=True, style_="margin-left: 40px; padding: 0 20px;", value=path):
                                                solara.v.ListItemContent(
                                                    children=[subitem.label],
                                                )
                            else:
                                path = "/documentation/" + route.path + ("/" + item.path if item.path != "/" else "")
                                with solara.Link(path):
                                    with solara.v.ListItem(dense=True, style_="padding: 0 20px;", value=path):
                                        solara.v.ListItemContent(
                                            children=[label],
                                        )
            with solara.Link("/contact"):
                with solara.v.ListItem(value="/contact"):
                    solara.v.ListItemIcon(children=[solara.v.Icon(children=["mdi-email"])])
                    solara.v.ListItemTitle(style_="padding: 0 20px;", children=["Contact"])
            with solara.Link("/changelog"):
                with solara.v.ListItem(value="/changelog"):
                    solara.v.ListItemIcon(children=[solara.v.Icon(children=["mdi-history"])])
                    solara.v.ListItemTitle(style_="padding: 0 20px;", children=["Changelog"])
            with solara.Link("/roadmap"):
                with solara.v.ListItem(value="/roadmap"):
                    solara.v.ListItemIcon(children=[solara.v.Icon(children=["mdi-road"])])
                    solara.v.ListItemTitle(style_="padding: 0 20px;", children=["Roadmap"])

    return main
