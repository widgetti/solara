from typing import Callable, Optional

import ipyvue as vue
import ipyvuetify as v

from solara.kitchensink import react, sol

routes = [
    sol.Route(path="/"),
    sol.Route(
        path="fruit",
        children=[
            sol.Route(path="kiwi"),
            sol.Route(path="banana"),
            sol.Route(path="apple"),
        ],
    ),
    sol.Route(
        path="blog",
        children=[
            sol.Route(path="/"),
            sol.Route(path="foo"),
            sol.Route(path="bar"),
        ],
    ),
    sol.Route(path="contact"),
]


def test_router():
    assert sol.routing.Router("", routes).path_routes == [routes[0]]
    assert sol.routing.Router("/fruit", routes).path_routes == [routes[1]]
    assert sol.routing.Router("/fruit/kiwi", routes).path_routes == [routes[1], routes[1].children[0]]
    assert sol.routing.Router("/fruit/pineapple", routes).path_routes == [routes[1]]
    assert sol.routing.Router("/fruit/apple", routes).path_routes == [routes[1], routes[1].children[-1]]

    assert sol.routing.Router("/blog", routes).path_routes == [routes[2], routes[2].children[0]]
    assert sol.routing.Router("/blog/doesnotexist", routes).path_routes == [routes[2]]
    assert sol.routing.Router("/blog/doesnotexist/more", routes).path_routes == [routes[2]]
    assert sol.routing.Router("/blog/foo", routes).path_routes == [routes[2], routes[2].children[1]]
    assert sol.routing.Router("/blog/foo/", routes).path_routes == [routes[2], routes[2].children[1]]

    assert sol.routing.Router("/doesnotexist", routes).path_routes == []


def test_resolve_path_route():
    @react.component
    def Test(route):
        return sol.Text(sol.resolve_path(route))

    @react.component
    def Provider(path, route):
        # nonlocal set_path
        path, set_path = sol.use_state_or_update(path)
        sol.routing._location_context.provide(sol.routing._Location(path, set_path))
        sol.routing.router_context.provide(sol.routing.Router(path, routes=routes))
        return Test(route)

    container, rc = react.render(Provider("/", routes[0]))
    assert rc._find(vue.Html).widget.children[0] == "/"

    container, rc = react.render(Provider("/", routes[1]))
    assert rc._find(vue.Html).widget.children[0] == "/fruit"
    container, rc = react.render(Provider("/", routes[1].children[1]))
    assert rc._find(vue.Html).widget.children[0] == "/fruit/banana"


def test_resolve_path_str():
    @react.component
    def Test(path: str):
        sol.use_route()
        return sol.Text(sol.resolve_path(path))

    @react.component
    def FruitProvider(path: str):
        path, set_path = sol.use_state_or_update(path)
        sol.routing._location_context.provide(sol.routing._Location(path, set_path))
        sol.routing.router_context.provide(sol.routing.Router("/fruit", routes=routes))
        sol.use_route()
        return Test(path)

    container, rc = react.render(FruitProvider("kiwi"))
    assert rc._find(vue.Html).widget.children[0] == "/fruit/kiwi"
    container, rc = react.render(FruitProvider("apple"))
    assert rc._find(vue.Html).widget.children[0] == "/fruit/apple"
    container, rc = react.render(FruitProvider("/fruit/apple"))
    assert rc._find(vue.Html).widget.children[0] == "/fruit/apple"


def test_toggle_buttons_single():
    value: Optional[str] = None
    set_path: Callable[[str], None] = lambda x: None

    def set(value_):
        nonlocal value
        value = value_

    routes = [
        sol.Route(path="/"),
        sol.Route(
            path="fruit",
            children=[
                sol.Route(path="kiwi"),
                sol.Route(path="banana"),
                sol.Route(path="apple"),
            ],
        ),
    ]

    @react.component
    def Test():
        route, routes = sol.use_route()
        if route is None:
            return sol.Button("Error!")
        assert sol.resolve_path(route.path) == f"/fruit/{route.path}"
        route_banana = sol.routing.find_route("banana")
        assert route_banana is not None
        assert route_banana.path == "banana"
        assert sol.resolve_path(route_banana.path) == "/fruit/banana"
        with sol.Link(sol.resolve_path(route_banana.path)) as main:
            sol.Button(route.path)
        return main

    @react.component
    def Root():
        route, routes = sol.use_route()
        assert sol.resolve_path("fruit") == "/fruit"
        assert sol.resolve_path("fruit/banana") == "/fruit/banana"
        assert route in routes
        assert route is not None
        assert route.path in ["fruit"]
        return Test()

    @react.component
    def Provider():
        nonlocal set_path
        path, set_path = react.use_state("/fruit/banana")

        sol.routing._location_context.provide(sol.routing._Location(path, set_path))
        sol.routing.router_context.provide(sol.routing.Router(path, routes=routes))
        return Root()

    container, rc = react.render(Provider(), handle_error=False)
    assert rc._find(v.Btn).widget.children[0] == "banana"
    set_path("/fruit/kiwi")
    assert rc._find(v.Btn).widget.children[0] == "kiwi"
    set_path("/fruit/wumpa")
    assert rc._find(v.Btn).widget.children[0] == "Error!"
