"""
# use_route

See also [Understanding Routing](/docs/understanding/routing).


```python
def use_route() -> Tuple[Optional[sol.Route], List[sol.Route]]:
    ...
```

`use_route` returns (if found) the current route that matches the pathname, or None. It also returns all resolved routes of that level
(i.e. all siblings and itself). This return tuple is useful to build custom navigation (e.g. using tabs or buttons).


Routing starts with declaring a set of `routes` in your app (solara picks up the `routes` variable if it exists,
and it should be in the same namespace as `Page`).
In the demo below, we declared the following routes.

```python
routes = [
    sol.Route(path="/"),
    sol.Route(
        path="fruit",
        component=Fruit,
        children=[
            sol.Route(path="/"),
            sol.Route(path="kiwi"),
            sol.Route(path="banana"),
            sol.Route(path="apple"),
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

from solara.kitchensink import react, sol


@react.component
def Fruit():
    # this gets all routes in fruit's children
    route, routes = sol.use_route()

    if route is None:
        with sol.Link("banana") as main:
            sol.Button("Fruit not found, go to banana")
        return main

    if route.path == "/":
        with sol.Link("banana") as main:
            sol.Button("Choose a fruit, I recomment banana")
        return main

    with sol.VBox() as main:
        with sol.HBox():
            for route_fruit in routes[1:]:
                with sol.Link(sol.resolve_path(route_fruit)):
                    sol.Button(route_fruit.path)

            with sol.Link("/api/use_route/fruit/nofruit"):
                sol.Button("Wrong fruit")
            with sol.Link("/api/use_route/not-routed"):
                sol.Button("Wrong url")
        sol.Success(f"You chose {route.path}")
    return main


@react.component
def Page():
    # this gets the top level routes, '/' and 'fruit'
    route_current, routes_all = sol.use_route()
    with sol.VBox() as main:
        with sol.Card("Navigation using buttons"):
            with sol.HBox():
                for route in routes_all:
                    with sol.Link(route):
                        sol.Button(route.path, color="red" if route_current == route else None)
        with sol.Card("Content decided by route:"):
            if route_current is None:
                sol.Error("Page does not exist")
                with sol.Link("fruit/kiwi"):
                    sol.Button("Go to fruit/kiwi")
            elif route_current.path == "/":
                with sol.Link("fruit/banana"):
                    sol.Button("Go to fruit/banana")
            elif route_current.path == "fruit":
                Fruit()
            else:
                sol.Error(f"Unknown route: {route_current.path}")
    return main


routes = [
    sol.Route(path="/"),
    sol.Route(
        path="fruit",
        component=Fruit,
        children=[
            sol.Route(path="/"),
            sol.Route(path="kiwi"),
            sol.Route(path="banana"),
            sol.Route(path="apple"),
        ],
    ),
]

sources = [Fruit.f, Page.f]  # type: ignore
