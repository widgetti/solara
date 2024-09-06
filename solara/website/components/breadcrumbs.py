from typing import List
import solara


@solara.component
def BreadCrumbs(route_current: solara.Route):
    router = solara.use_router()
    current_path_parts = solara.resolve_path(route_current).split("/")
    print("Current path parts", current_path_parts)
    routes: List[solara.Route] = _resolve_path_to_route(current_path_parts[1:], router.routes, [])
    print("Found routes", [r.path for r in routes])

    with solara.Row(style={"align-items": "center", "flex-wrap": "wrap"}) as main:
        for i, route in enumerate(routes):
            if i == len(routes) - 1:
                solara.Text(route.label, style={"color": "var(--color-text-fade)"})
            else:
                with solara.Link(solara.resolve_path(route), style={"color": "var(--color-text-fade)"}):
                    solara.Text(route.label)
            if i != len(routes) - 1:
                solara.Text("/", style={"font-size": "1.5rem", "color": "var(--color-text-fade)"})
    return main


def _resolve_path_to_route(path_to_find: List[str], all_routes: List[solara.Route], routes: List[solara.Route] = []):
    if len(path_to_find) == 0:
        return routes
    for route in all_routes:
        if path_to_find[0] == route.path:
            routes += [route]
            return _resolve_path_to_route(path_to_find[1:], route.children, routes)
