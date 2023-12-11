"""# resolve_route

"""
import solara
from solara.website.utils import apidoc

title = "resolve_route"
routes = [
    solara.Route(path="/"),
    solara.Route(path="kiwi"),
    solara.Route(path="banana"),
    solara.Route(path="apple"),
]


@solara.component
def Page():
    route_current, routes = solara.use_route()
    with solara.VBox() as main:
        # solara.Warning("Note the address bar in the browser. It should change to the path of the link.")
        solara.Markdown("*Click on one of the links below to change the route and see the url in your browser change, and match the text.*")
        with solara.VBox():
            for route in routes:
                path = solara.resolve_path(route)
                # we could have passed the route object directly to Link, but we want to show the path
                # can also be used.
                with solara.Link(path):
                    current = route_current is route
                    if current:
                        solara.Success(f"You are at {path}")
                    else:
                        solara.Info(f"{route.path} will navigate to {path}")
    return main


__doc__ += apidoc(solara.resolve_path)  # type: ignore
