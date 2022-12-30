from typing import Callable, Optional

import ipyvue as vue
import ipyvuetify as v

import solara

routes = [
    solara.Route(path="/"),
    solara.Route(
        path="fruit",
        children=[
            solara.Route(path="kiwi"),
            solara.Route(path="banana"),
            solara.Route(path="apple"),
        ],
    ),
    solara.Route(
        path="blog",
        children=[
            solara.Route(path="/"),
            solara.Route(path="foo"),
            solara.Route(path="bar"),
        ],
    ),
    solara.Route(path="contact"),
]


def test_router():
    assert solara.routing.Router("", routes).path_routes == [routes[0]]
    assert solara.routing.Router("/fruit", routes).path_routes == [routes[1]]
    assert solara.routing.Router("/fruit/kiwi", routes).path_routes == [routes[1], routes[1].children[0]]

    assert solara.routing.Router("/fruit/pineapple", routes).path_routes == [routes[1]]
    assert solara.routing.Router("/fruit/apple", routes).path_routes == [routes[1], routes[1].children[-1]]

    assert solara.routing.Router("/blog", routes).path_routes == [routes[2], routes[2].children[0]]
    assert solara.routing.Router("/blog/doesnotexist", routes).path_routes == [routes[2]]
    assert solara.routing.Router("/blog/doesnotexist/more", routes).path_routes == [routes[2]]
    assert solara.routing.Router("/blog/foo", routes).path_routes == [routes[2], routes[2].children[1]]
    assert solara.routing.Router("/blog/foo/", routes).path_routes == [routes[2], routes[2].children[1]]

    assert solara.routing.Router("/doesnotexist", routes).path_routes == []

    assert solara.routing.Router("?a=1", routes).path_routes == [routes[0]]
    assert solara.routing.Router("?a=1", routes).search == "a=1"
    assert solara.routing.Router("/fruit?b=1&c=3", routes).path_routes == [routes[1]]

    # non-existing routes, as leafs are fine, since they can do 'subrouting'
    assert solara.routing.Router("/fruit/kiwi/sub", routes).path_routes == [routes[1], routes[1].children[0]]
    assert solara.routing.Router("/fruit/kiwi/sub", routes).possible_match

    # but if there are sublings, it should not exist
    assert solara.routing.Router("/fruit/chocolate", routes).path_routes == [routes[1]]
    assert not solara.routing.Router("/fruit/chocolate", routes).possible_match

    assert solara.routing.Router("/fruit/chocolate", routes).path_routes == [routes[1]]
    assert not solara.routing.Router("/fruit/chocolate/sub", routes).possible_match

    assert solara.routing.Router("/foo", routes).path_routes == []
    assert not solara.routing.Router("/foo", routes).possible_match
    assert solara.routing.Router("/foo/bar", routes).path_routes == []
    assert not solara.routing.Router("/foo/bar", routes).possible_match


def test_resolve_path_route():
    @solara.component
    def Test(route):
        return solara.Text(solara.resolve_path(route))

    @solara.component
    def Provider(path, route):
        # nonlocal set_path
        path, set_path = solara.use_state_or_update(path)
        solara.routing._location_context.provide(solara.routing._Location(path, set_path))
        solara.routing.router_context.provide(solara.routing.Router(path, routes=routes))
        return Test(route)

    container, rc = solara.render(Provider("/", routes[0]))
    assert rc._find(vue.Html).widget.children[0] == "/"

    container, rc = solara.render(Provider("/", routes[1]))
    assert rc._find(vue.Html).widget.children[0] == "/fruit"
    container, rc = solara.render(Provider("/", routes[1].children[1]))
    assert rc._find(vue.Html).widget.children[0] == "/fruit/banana"


def test_resolve_path_str():
    @solara.component
    def Test(path: str):
        solara.use_route()
        return solara.Text(solara.resolve_path(path))

    @solara.component
    def FruitProvider(path: str):
        path, set_path = solara.use_state_or_update(path)
        solara.routing._location_context.provide(solara.routing._Location(path, set_path))
        solara.routing.router_context.provide(solara.routing.Router("/fruit", routes=routes))
        solara.use_route()
        return Test(path)

    container, rc = solara.render(FruitProvider("kiwi"))
    assert rc._find(vue.Html).widget.children[0] == "/fruit/kiwi"
    container, rc = solara.render(FruitProvider("apple"))
    assert rc._find(vue.Html).widget.children[0] == "/fruit/apple"
    container, rc = solara.render(FruitProvider("/fruit/apple"))
    assert rc._find(vue.Html).widget.children[0] == "/fruit/apple"


def test_toggle_buttons_single():
    value: Optional[str] = None
    set_path: Callable[[str], None] = lambda x: None

    def set(value_):
        nonlocal value
        value = value_

    routes = [
        solara.Route(path="/"),
        solara.Route(
            path="fruit",
            children=[
                solara.Route(path="kiwi"),
                solara.Route(path="banana"),
                solara.Route(path="apple"),
            ],
        ),
    ]

    @solara.component
    def Test():
        route, routes = solara.use_route()
        if route is None:
            return solara.Button("Error!")
        assert solara.resolve_path(route.path) == f"/fruit/{route.path}"
        route_banana = solara.routing.find_route("banana")
        assert route_banana is not None
        assert route_banana.path == "banana"
        assert solara.resolve_path(route_banana.path) == "/fruit/banana"
        with solara.Link(solara.resolve_path(route_banana.path)) as main:
            solara.Button(route.path)
        return main

    @solara.component
    def Root():
        route, routes = solara.use_route()
        assert solara.resolve_path("fruit") == "/fruit"
        assert solara.resolve_path("fruit/banana") == "/fruit/banana"
        assert route in routes
        assert route is not None
        assert route.path in ["fruit"]
        return Test()

    @solara.component
    def Provider():
        nonlocal set_path
        path, set_path = solara.use_state("/fruit/banana")

        solara.routing._location_context.provide(solara.routing._Location(path, set_path))
        solara.routing.router_context.provide(solara.routing.Router(path, routes=routes))
        return Root()

    container, rc = solara.render(Provider(), handle_error=False)
    assert rc._find(v.Btn).widget.children[0] == "banana"
    set_path("/fruit/kiwi")
    assert rc._find(v.Btn).widget.children[0] == "kiwi"
    set_path("/fruit/wumpa")
    assert rc._find(v.Btn).widget.children[0] == "Error!"
