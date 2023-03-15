import abc
import logging
import urllib.parse
from typing import Callable, List, Optional, Tuple, TypeVar, Union, cast

import solara
from solara import _using_solara_server

logger = logging.getLogger("solara.router")
T = TypeVar("T")


class _LocationBase(abc.ABC):
    @property
    def pathname(self):
        pass

    @pathname.setter
    # mypy does not accept this
    # @abc.abstractmethod
    def pathname(self):
        pass


class _Location(_LocationBase):
    def __init__(self, pathname, setter: Callable[[str], None]) -> None:
        self._pathname = pathname
        self.setter = setter

    @property
    def pathname(self):
        return self._pathname

    @pathname.setter
    def pathname(self, value):
        # import pdb

        # pdb.set_trace()
        self._pathname = value
        self.setter(self._pathname)


class Router:
    search: Optional[str]

    def __init__(self, path: str, routes: List[solara.Route], set_path: Callable[[str], None] = None):
        # see https://developer.mozilla.org/en-US/docs/Web/API/Location for anatomy/nomenclature
        if "?" in path:
            self.path, self.search = path.split("?", 1)
        else:
            self.path = path
            self.search = None
        del path
        self.set_path = set_path
        self.parts = (self.path or "").strip("/").split("/")
        self.routes = routes
        self.root_path = ""
        if _using_solara_server():
            import solara.server.settings

            self.root_path = solara.server.settings.main.root_path or ""
        # each route in this list corresponds to a part in self.parts
        self.path_routes: List["solara.Route"] = []
        self.path_routes_siblings: List[List["solara.Route"]] = []  # siblings including itself
        # routes = routes.copy()
        route = None
        for part in self.parts:
            for route in routes:
                if (route.path == part) or (route.path == "/" and not part):
                    self.path_routes.append(route)
                    self.path_routes_siblings.append(routes)
                    routes = route.children
                    break
        if len(self.parts) == len(self.path_routes):
            # e.g. '/foo/bar' -> ['foo', 'bar'] and bar has a default route
            # but if '' -> [''] we should not
            route = self.path_routes[-1]
            if route:
                default_routes = [k for k in route.children if k.path == "/"]
                if self.parts and self.parts[0] and default_routes:
                    self.path_routes.append(default_routes[0])
                    self.path_routes_siblings.append(route.children)

        assert len(self.path_routes) == len(self.path_routes_siblings)
        self.possible_match = (len(self.path_routes[-1].children) == 0) if self.path_routes else False

    def push(self, path: str):
        assert self.set_path is not None
        self.set_path(path)


router_context = solara.create_context(Router("", []))
_location_context = solara.create_context(cast(_LocationBase, _Location("", lambda x: None)))

route_level_context = solara.create_context(0)


def use_route_level():
    route_level = solara.use_context(route_level_context)
    return route_level


def use_router() -> Router:
    return solara.use_context(router_context)


def use_route(level=0) -> Tuple[Optional[solara.Route], List[solara.Route]]:
    router = solara.use_context(router_context)
    route_level = solara.use_context(route_level_context)
    route_level_context.provide(route_level + 1)
    route_level += level
    if route_level < len(router.path_routes):
        return router.path_routes[route_level], router.path_routes_siblings[route_level]
    else:
        return None, []


def find_route(path: str) -> Optional[solara.Route]:
    router = solara.use_context(router_context)
    route_level = min(solara.use_context(route_level_context), len(router.path_routes_siblings) - 1)
    for route in router.path_routes_siblings[route_level]:
        if path.startswith(route.path) or (not path and route.path == "/"):
            return route
    return None


def use_pathname():
    location_proxy = solara.use_context(_location_context)

    def setter(value):
        location_proxy.pathname = value

    return location_proxy.pathname, setter


def resolve_path(path_or_route: Union[str, solara.Route], level=0) -> str:
    """Resolve a relative path or a route to an absolute path.

    If the path is a string and starts with a `/'`, it is returned as is.


    ## Typical usage:

    ```python
    ...
    route_current, routes_current_level = solara.routes()
    # route_current.path == "banana"
    path = solara.resolve_path(route_current)
    # path == "/fruit/banana"
    path_same = solara.resolve_path("banana")
    # path_same == path == "/fruit/banana"
    ...
    ```

    ## Arguments

     * path_or_route: a path string or a [`solara.Route`](/api/route) object to resolve.

    ## See also

     * [Multipage](/docs/howto/multipage).
     * [Understanding Routing](/docs/understanding/routing).


    """
    router = solara.use_context(router_context)
    if isinstance(path_or_route, str):
        path = path_or_route
        if path.startswith("/"):
            return path
        route_level = solara.use_context(route_level_context) + level - 1
        parts = [*router.parts[:route_level], path]
        path = "/" + "/".join(parts)
        if path.startswith("//"):
            path = path[1:]
        return path
    elif isinstance(path_or_route, solara.Route):
        route: solara.Route = path_or_route
        path = _resolve_path("/", route, router.routes)
        if path.startswith("//"):
            path = path[1:]
        return path


def _resolve_path(prefix: str, findroute: solara.Route, routes: List[solara.Route]):
    for route in routes:
        path = (prefix + "/" + route.path) if route.path != "/" else prefix
        if findroute is route:
            return path
        possible_path = _resolve_path(path, findroute=findroute, routes=route.children)
        if possible_path is not None:
            return possible_path


def use_query_parameter(
    name: str,
    default: T,
    from_string: Callable[[str], T],
    to_string: Callable[[T], str] = str,
) -> Tuple[T, Callable[[T], None]]:
    """Store state in a query parameter, which is part of the URL.

    Can be used as a replacement for `use_state`, but the state is stored in the URL,
    so an url can be shared with others, or bookmarked.

    For instance [Give 10 thumbs up by clicking on /api/use_query_parameter?count=10](/api/use_query_parameter?count=10)
    will change the count query parameter to 10.

    ## Typical usage:

    ```python
    import solara

    @solara.component
    def Page():
        count, set_count = solara.use_query_parameter("count", 2, int)
        if count > 0:
            solara.Text(f"👍" * count)
        if count == 0:
            solara.Text("🤔")
        else:
            solara.Text(f"👎" * (-count))
        solara.Button("Increment", on_click=lambda: set_count(count + 1))
        solara.Button("Decrement", on_click=lambda: set_count(count - 1))
    ```

    ## Arguments

     * name: the name of the query parameter.
     * default: the default value of the query parameter.
     * from_string: a function to convert the value of the query parameter to the desired type.
     * to_string: a function to convert the value of the query parameter to a string.
    """
    router = use_router()

    values = urllib.parse.parse_qs(router.search, keep_blank_values=True)

    def setter(value: T):
        values = urllib.parse.parse_qs(router.search, keep_blank_values=True)
        if solara.equals(value, default):
            values.pop(name, None)
        else:
            values[name] = [to_string(value)]
        path = router.path
        if values:
            path += "?" + urllib.parse.urlencode(values, doseq=True)
        router.push(path)

    if name in values:
        string_value = values[name][0]
        typed_value = from_string(string_value) if string_value is not None else default
    else:
        typed_value = default
    return typed_value, setter
