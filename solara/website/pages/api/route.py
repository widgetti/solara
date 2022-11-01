"""# Route

"""
import solara
from solara.website.utils import apidoc

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
        solara.Markdown("*Click on one of the links below to change the route and see the url in your browser change, and match the route.*")
        with solara.VBox():
            for route in routes:
                with solara.Link(route):
                    current = route_current is route
                    if current:
                        solara.Success(f"You are at solara.Route(path={route.path!r})")
                    else:
                        solara.Info(f"Go to solara.Route(path={route.path!r})")
    return main


__doc__ += apidoc(solara.Route, full=True)  # type: ignore
