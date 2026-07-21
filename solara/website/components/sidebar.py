from solara.util import IPYVUETIFY_V3

if IPYVUETIFY_V3:
    import solara

    @solara.component
    def Sidebar():
        route_current, all_routes = solara.use_route(-1)
        router = solara.use_router()
        link_style = {"color": "inherit", "text-decoration": "none"}
        if route_current is None:
            return solara.Error("Page not found")

        # Pick out documentation route, so we can use this on any page
        for route in all_routes:
            if route.path == "documentation":
                all_routes = route.children
                break

        opened = []
        for route in all_routes:
            path_top_level = "/documentation/" + route.path
            if router.path.startswith(path_top_level):
                opened.append(path_top_level)
                for item in route.children:
                    path_sub = "/documentation/" + route.path + "/" + item.path
                    if router.path.startswith(path_sub):
                        opened.append(path_sub)

        with solara.v.List(
            class_="docs-sidebar-list",
            color="#ff991f",
            selected=[router.path],
            opened=opened,
            style_="height: 100%; max-height: 100vh; display: flex; flex-direction: column; background-color: var(--color-material-background); overflow-y: auto; padding: 8px;",
        ) as main:
            # e.g. getting_started, examples, components, api, advanced, faq
            for route in all_routes:
                if len(route.children) == 1 or route.path == "/":
                    with solara.Link("/documentation/" + route.path if route.path != "/" else "/documentation", style=link_style):
                        solara.v.ListItem(
                            value="/documentation/" + route.path if route.path != "/" else "/documentation",
                            prepend_icon="mdi-home" if route.path == "/" else None,
                            min_height=56 if route.path == "/" else None,
                            class_="docs-sidebar-home-item" if route.path == "/" else None,
                            title=route.label,
                            style_="padding: 0 20px;",
                        )
                else:
                    path_top_level = "/documentation/" + route.path
                    # v_bind is inherited from the Vue widget base but missing from the generated wrapper signature.
                    activator = solara.v.ListItem(title=route.label, style_="padding: 0 20px;", v_bind="x.props")  # type: ignore[call-arg]
                    with solara.v.ListGroup(
                        value=path_top_level,
                        v_slots=[{"name": "activator", "variable": "x", "children": activator}],
                    ):
                        for item in route.children:
                            label = item.label
                            if item.path == "/" and route.path in ["examples", "api", "components"]:
                                # the 'homepage' of the subpage are named Overview
                                label = "Overview"
                            path_sub = "/documentation/" + route.path + "/" + item.path
                            if item.children != [] and any([c.label is not None and c.path != "/" for c in item.children]):
                                activator = solara.v.ListItem(  # type: ignore[call-arg]
                                    title=label,
                                    min_height=56,
                                    style_="--indent-padding: 0px; --list-indent-size: 0px; padding: 0 20px;",
                                    v_bind="x.props",
                                )
                                with solara.v.ListGroup(
                                    value=path_sub,
                                    subgroup=True,
                                    v_slots=[{"name": "activator", "variable": "x", "children": activator}],
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
                                            style=link_style,
                                        ):
                                            solara.v.ListItem(
                                                density="compact", style_="--indent-padding: 56px; padding: 0 20px;", value=path, title=subitem.label
                                            )
                            else:
                                path = "/documentation/" + route.path + ("/" + item.path if item.path != "/" else "")
                                with solara.Link(path, style=link_style):
                                    solara.v.ListItem(density="compact", style_="--indent-padding: 4px; padding: 0 20px;", value=path, title=label)
            with solara.Link("/contact", style=link_style):
                solara.v.ListItem(value="/contact", prepend_icon="mdi-email", min_height=56, title="Contact", style_="padding: 0 20px;")
            with solara.Link("/changelog", style=link_style):
                solara.v.ListItem(value="/changelog", prepend_icon="mdi-history", min_height=56, title="Changelog", style_="padding: 0 20px;")
            with solara.Link("/roadmap", style=link_style):
                solara.v.ListItem(value="/roadmap", prepend_icon="mdi-road", min_height=56, title="Roadmap", style_="padding: 0 20px;")

        return main
else:
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


__all__ = ["Sidebar"]
