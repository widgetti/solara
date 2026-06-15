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
        nav=True,
        selected=[router.path],
        opened=opened,
        style_="height: 100%; max-height: 100vh; display: flex; flex-direction: column; background-color: var(--color-material-background); overflow-y: auto;",
    ) as main:
        # e.g. getting_started, examples, components, api, advanced, faq
        for route in all_routes:
            if len(route.children) == 1 or route.path == "/":
                with solara.Link("/documentation/" + route.path if route.path != "/" else "/documentation"):
                    solara.v.ListItem(
                        value="/documentation/" + route.path if route.path != "/" else "/documentation",
                        prepend_icon="mdi-home" if route.path == "/" else None,
                        title=route.label,
                        style_="padding: 0 20px;",
                    )
            else:
                path_top_level = "/documentation/" + route.path
                activator = solara.v.ListItem(title=route.label, style_="padding: 0 20px;", v_bind="x.props")
                with solara.v.ListGroup(
                    value=path_top_level,
                    v_slots=[{"name": "activator", "variable": "x", "children": activator}],
                    style_="padding: 0 20px;",
                ):
                    for item in route.children:
                        label = item.label
                        if item.path == "/" and route.path in ["examples", "api", "components"]:
                            # the 'homepage' of the subpage are named Overview
                            label = "Overview"
                        path_sub = "/documentation/" + route.path + "/" + item.path
                        if item.children != [] and any([c.label is not None and c.path != "/" for c in item.children]):
                            activator = solara.v.ListItem(title=label, density="compact", style_="padding: 0 20px;", v_bind="x.props")
                            with solara.v.ListGroup(
                                value=path_sub,
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
                                    ):
                                        solara.v.ListItem(density="compact", style_="margin-left: 40px; padding: 0 20px;", value=path, title=subitem.label)
                        else:
                            path = "/documentation/" + route.path + ("/" + item.path if item.path != "/" else "")
                            with solara.Link(path):
                                solara.v.ListItem(density="compact", style_="padding: 0 20px;", value=path, title=label)
        with solara.Link("/contact"):
            solara.v.ListItem(value="/contact", prepend_icon="mdi-email", title="Contact", style_="padding: 0 20px;")
        with solara.Link("/changelog"):
            solara.v.ListItem(value="/changelog", prepend_icon="mdi-history", title="Changelog", style_="padding: 0 20px;")
        with solara.Link("/roadmap"):
            solara.v.ListItem(value="/roadmap", prepend_icon="mdi-road", title="Roadmap", style_="padding: 0 20px;")

    return main
