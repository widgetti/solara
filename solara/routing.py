import abc
import logging
from typing import Callable, List, Optional, Tuple, Union, cast

import solara

logger = logging.getLogger("solara.router")


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
    def __init__(self, path: str, routes: List[solara.Route], set_path: Callable[[str], None] = None):
        self.path = path
        self.set_path = set_path
        self.parts = (path or "").strip("/").split("/")
        self.routes = routes
        # each route in this list corresponds to a part in self.parts
        self.path_routes: List[solara.Route] = []
        self.path_routes_siblings = []  # siblings including itself
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
