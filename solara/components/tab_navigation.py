import solara
from solara.alias import rv, rvue
from solara.util import IPYVUETIFY_V3


@solara.component
def LinkTab(path, label):
    # both adding href to tab or adding Link makes vuetify buggy
    with rv.Tab() as tab:
        # with solara.Link(path):
        solara.Text(label)
    router = solara.use_router()

    def go(*ignore):
        router.push(path)

    rvue.use_event(tab, "click.prevent.stop", go)
    return tab


@solara.component
def TabNavigation(children=[], vertical=False, **kwargs):
    children = children or []
    route_current, all_routes = solara.use_route()

    tab_index = all_routes.index(route_current) if route_current is not None else 0

    if IPYVUETIFY_V3:
        tabs = rv.Tabs(v_model=tab_index, direction="vertical" if vertical else None, **kwargs)
    else:
        tabs = rv.Tabs(v_model=tab_index, vertical=vertical, **kwargs)
    with tabs as main:
        for i, route in enumerate(all_routes):
            path = solara.resolve_path(route)
            LinkTab(path, route.label or "No title")
        if route_current is None:
            return solara.Error("Page does not exist")

        if IPYVUETIFY_V3:
            rv.Window(v_model=tab_index, children=children)
        else:
            rv.TabsItems(v_model=tab_index, children=children)

    return main
