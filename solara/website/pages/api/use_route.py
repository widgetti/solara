"""
# use_route
"""

import solara
from solara.website.utils import apidoc

title = "use_route"


@solara.component
def Fruit():
    # this gets all routes in fruit's children
    route, routes = solara.use_route()

    if route is None:
        with solara.Link("banana") as main:
            solara.Button("Fruit not found, go to banana")
        return main

    if route.path == "/":
        with solara.Link("banana") as main:
            solara.Button("Choose a fruit, I recomment banana")
        return main

    with solara.VBox() as main:
        with solara.HBox():
            for route_fruit in routes[1:]:
                with solara.Link(solara.resolve_path(route_fruit)):
                    solara.Button(route_fruit.path)

            with solara.Link("/api/use_route/fruit/nofruit", nofollow=True):
                solara.Button("Wrong fruit")
            with solara.Link("/api/use_route/not-routed", nofollow=True):
                solara.Button("Wrong url")
        solara.Success(f"You chose {route.path}")
    return main


@solara.component
def Page():
    # this gets the top level routes, '/' and 'fruit'
    route_current, routes_all = solara.use_route()
    with solara.VBox() as main:
        with solara.Card("Navigation using buttons"):
            with solara.HBox():
                for route in routes_all:
                    with solara.Link(route):
                        solara.Button(route.path, color="red" if route_current == route else None)
        with solara.Card("Content decided by route:"):
            if route_current is None:
                solara.Error("Page does not exist")
                with solara.Link("fruit/kiwi"):
                    solara.Button("Go to fruit/kiwi")
            elif route_current.path == "/":
                with solara.Link("fruit/banana"):
                    solara.Button("Go to fruit/banana")
            elif route_current.path == "fruit":
                Fruit()
            else:
                solara.Error(f"Unknown route: {route_current.path}")
    return main


routes = [
    solara.Route(path="/"),
    solara.Route(
        path="fruit",
        component=Fruit,
        children=[
            solara.Route(path="/"),
            solara.Route(path="kiwi"),
            solara.Route(path="banana"),
            solara.Route(path="apple"),
        ],
    ),
]

sources = [Fruit.f, Page.f]  # type: ignore
__doc__ += apidoc(solara.use_route)  # type: ignore
