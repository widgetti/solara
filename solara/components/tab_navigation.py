from solara.alias import react, rv, rvue, sol


@react.component
def LinkTab(path, label):
    # both adding href to tab or adding Link makes vuetify buggy
    with rv.Tab() as tab:
        # with sol.Link(path):
        sol.Text(label)
    router = sol.use_router()

    def go(*ignore):
        router.push(path)

    rvue.use_event(tab, "click.prevent.stop", go)
    return tab


@react.component
def TabNavigation(children=[], vertical=False, **kwargs):
    children = children or []
    route_current, all_routes = sol.use_route()

    tab_index = all_routes.index(route_current) if route_current is not None else 0

    with rv.Tabs(v_model=tab_index, vertical=vertical, **kwargs) as main:
        for i, route in enumerate(all_routes):
            path = sol.resolve_path(route)
            LinkTab(path, route.label or "No title")
        if route_current is None:
            return sol.Error("Page does not exist")

        with rv.TabsItems(v_model=tab_index, children=children):
            pass

    return main
