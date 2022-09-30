"""
# use_route

See also [Understanding Routing](/docs/understanding/routing).


```python
def use_route() -> Tuple[Optional[solara.Route], List[solara.Route]]:
    ...
```

`use_route` returns (if found) the current route that matches the pathname, or None. It also returns all resolved routes of that level
(i.e. all siblings and itself). This return tuple is useful to build custom navigation (e.g. using tabs or buttons).


Routing starts with declaring a set of `routes` in your app (solara picks up the `routes` variable if it exists,
and it should be in the same namespace as `Page`).
In the demo below, we declared the following routes.

```python
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
```

Note that all routes are relative, since a component does not know if it is embedded into a larger application, which may also do routing.
Therefore you should never use the `route.path` for navigation since the route object has no knowledge of the full url
(e.g. `/api/use_route/fruit/banana`) but only knows its small piece of the pathname (e.g. `banana`)

Use [`resolve_path`](/api/resolve_path) to request the full url for navigation, or simply use the `Link` component that can do this for us.

If the current route has children, any child component that calls `use_route` will return the matched route and its siblings of our children.


"""

import solara


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

            with solara.Link("/api/use_route/fruit/nofruit"):
                solara.Button("Wrong fruit")
            with solara.Link("/api/use_route/not-routed"):
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
