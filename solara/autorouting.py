import importlib
import inspect
import pkgutil
import re
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, List, Optional, cast

import reacton
import reacton.core

import solara
from solara.alias import rv
from solara.util import cwd

from .server import reload

autoroute_level_context = solara.create_context(0)
DEBUG = False


def source_to_module(path: Path) -> ModuleType:
    fullname = path.stem
    mod = ModuleType(fullname)
    mod.__file__ = str(path)
    if path.suffix == ".py":
        with open(path) as f:
            ast = compile(f.read(), path, "exec")
            exec(ast, mod.__dict__)
    elif path.suffix == ".ipynb":
        import nbformat

        nb: nbformat.NotebookNode = nbformat.read(path, 4)
        with cwd(Path(path).parent):
            for cell_index, cell in enumerate(nb.cells):
                cell_index += 1  # used 1 based
                if cell.cell_type == "code":
                    source = cell.source
                    cell_path = f"{path} input cell {cell_index}"
                    ast = compile(source, cell_path, "exec")
                    exec(ast, mod.__dict__)
    else:
        raise TypeError(f"Only .py and .ipynb supported (not {path})")
    return mod


def count_arguments(f: Callable):
    if isinstance(f, reacton.core.ComponentFunction):
        f = f.f
    sig = inspect.signature(f)
    return len([k for name, k in sig.parameters.items() if (k.default == k.empty) and (k.kind != k.VAR_POSITIONAL) and (k.kind != k.VAR_KEYWORD)])


def arg_cast(args: List[str], f: Callable):
    if isinstance(f, reacton.core.ComponentFunction):
        f = f.f
    sig = inspect.signature(f)
    results = []
    for i, (name, param) in enumerate(sig.parameters.items()):
        if i >= len(args):
            break
            # TODO: can we give a better error message?
            # raise TypeError(f"{f} expected positional argument {param}, but not enought argument supplied")
        annotation = param.annotation
        value = args[i]
        if annotation == param.empty:
            results.append(value)
        else:
            try:
                results.append(annotation(value))
            except Exception as e:
                raise ValueError(f"Cannot cast argument {name} of {f} to type {annotation} with value {value}") from e
    return results


@solara.component
def RoutingProvider(children: List[reacton.core.Element] = [], routes: List[solara.Route] = [], pathname: str = ""):
    """Wraps the app, adds extra context, like navigation/routing."""
    path, set_path = solara.use_state_or_update(pathname, key="solara-context-path")
    nav = solara.Navigator(location=path, on_location=set_path)
    solara.routing._location_context.provide(solara.routing._Location(path, set_path))
    solara.routing.router_context.provide(solara.routing.Router(path, routes=routes, set_path=set_path))

    main = solara.VBox(
        children=[
            nav,
            *children,
        ]
    )

    return main


@solara.component
def RenderPage():
    """Renders the page that matches the route."""
    level_start = solara.use_route_level()
    router = solara.use_context(solara.routing.router_context)

    if len(router.path_routes) <= level_start:
        with solara.VBox() as main:
            solara.Error(f"Page not found: {router.path}, len(router.path_routes)={len(router.path_routes)} <= level_start={level_start}")
            parent = "/" + "/".join(router.parts[:-1])
            with solara.Link(parent):
                solara.Button(f"Go to parent: {parent}", text=True)
            if DEBUG:
                from solara.components.captureoutput import CaptureOutput
                from solara.core import pp

                with CaptureOutput():
                    pp(router.routes)
        return main

    level_max = level_start
    layouts = []  # nested layouts
    # find the 'RenderPage' sentinel value to find the deepest level we should render
    for level in range(level_start, len(router.path_routes)):
        # we always level_start the 'package'/'root' layout
        roots = [k for k in router.path_routes_siblings[level] if k.path == "/"]
        if len(roots) == 1:
            root = roots[0]
            if root.layout:
                layouts.append(root.layout)
        route = router.path_routes[level]
        # and, if not the root layout, include the layout for the current route
        if route.path != "/" and route.layout:
            layouts.append(route.layout)
        if route.component is RenderPage:
            level_max = level
    route_current = router.path_routes[level_max]
    routes_siblings = router.path_routes_siblings[level_max]
    routes_siblings_index = routes_siblings.index(route_current)
    # if no layouts are found, we use the default layout
    if layouts == []:
        # except when the root routes has no siblings (maybe we should include no children?)
        if len(router.path_routes_siblings[level_start]) == 1:
            layouts = []
        else:
            layouts = [DefaultLayout]
    if route_current.data is None and route_current.module is None:
        return solara.Error(f"Page not found: {router.path}, route does not link to a path or module")

    def wrap_in_layouts(element: reacton.core.Element, layouts):
        for Layout in reversed(layouts):
            element = Layout(children=[element])
        return element

    def get_args(f):
        if len(router.path_routes) < len(router.parts):
            arg_strings = router.parts[len(router.path_routes) :]
            args = arg_cast(arg_strings, f)
            return args[: count_arguments(f)]
        else:
            return []

    if isinstance(route_current.data, Path):
        path = cast(Path, route_current.data)
        if path.suffix == ".md":
            with solara.HBox() as navigation:
                if routes_siblings_index > 0:
                    prev = routes_siblings[routes_siblings_index - 1]
                    with solara.Link(prev):
                        solara.Button(f"{prev.label}", text=True, icon_name="mdi-arrow-left")
                rv.Spacer()
                if routes_siblings_index < len(routes_siblings) - 1:
                    next = routes_siblings[routes_siblings_index + 1]
                    with solara.Link(next):
                        solara.Button(f"{next.label}", text=True, icon_name="mdi-arrow-right")
            main = solara.Div(
                children=[
                    solara.Title(route_current.label or "No title"),
                    solara.Markdown(path.read_text(), unsafe_solara_execute=True),
                    navigation,
                ]
            )
            main = wrap_in_layouts(main, layouts)
        else:
            main = solara.Error(f"Suffix {path.suffix} not supported")
    else:
        assert route_current.module is not None
        title = route_current.label or "No title"
        if route_current.module and hasattr(route_current.module, "title"):
            title = route_current.module.title
            if callable(title):
                title = title(*get_args(title))
        title_element = solara.Title(title)
        module = route_current.module
        namespace = module.__dict__
        if "app" in namespace:
            element = namespace["app"]
            main = solara.Div(
                children=[
                    title_element,
                    element,
                ]
            )
            main = wrap_in_layouts(main, layouts)
        elif "Page" in namespace:
            Page = get_page(module)
            args = get_args(Page)
            main = solara.Div(
                children=[
                    title_element,
                    Page(*args),
                ]
            )
            main = wrap_in_layouts(main, layouts)
        else:
            with DefaultLayout(router_level=-1) as main:
                solara.Error(f"{module} does not have a Page component or an app element")
    return main


@solara.component
def DefaultLayout(children: List[reacton.core.Element] = [], router_level=-1):
    route_current, all_routes = solara.use_route()
    router = solara.use_router()
    selected = router.path

    with solara.HBox(grow=True) as main:
        with rv.NavigationDrawer(right=False, width="400px", v_model=True, permanent=True):
            with rv.List(dense=True):
                with rv.ListItemGroup(v_model=selected):
                    for route in all_routes:
                        if route.children and route.data is None:
                            with solara.ListItem(route.label):
                                for child in route.children:
                                    path = solara.resolve_path(child)
                                    with solara.Link(path):
                                        title = child.label or "no label"
                                        if callable(title):
                                            title = "Error: dynamic title"
                                        solara.ListItem(title, value=path)
                        else:
                            path = solara.resolve_path(route)
                            with solara.Link(path):
                                solara.ListItem(route.label, value=path)
        with solara.Padding(4):
            solara.Div(children=children)
    return main


def get_page(module: ModuleType, required=True):
    page = getattr(module, "Page", None)
    if required and page is None:
        raise NameError(f"No component names 'Page' in module {module}")
    return page


def get_renderable(module: ModuleType, required=False):
    var_names = "app Page page".split()
    for var_name in var_names:
        entry = getattr(module, var_name, None)
        if entry:
            return entry
    if required:
        raise NameError(f"No component, element or widget found in module {module} with names: {', '.join(var_names[:-1])} or {var_names[-1]}")
    return entry


def get_title(module: ModuleType, required=True):
    assert module.__file__ is not None
    name = Path(module.__file__).stem
    if hasattr(module, "title"):
        title = module.title
    else:
        title_parts = re.split("[\\-_ ]+", name)
        title = " ".join(k.title() for k in title_parts)
    return title


def generate_routes(module: ModuleType) -> List[solara.Route]:
    assert module.__file__ is not None
    routes = []
    if module.__file__.endswith("__init__.py"):
        if hasattr(module, "routes"):
            # if routes if provided, use them instead of us generating them
            children = getattr(module, "routes")
            return children
        route_order = getattr(module, "route_order", None)
        layout = getattr(module, "Layout", None)
        title = get_title(module)
        children = getattr(module, "routes", [])
        routes.append(solara.Route(path="/", component=RenderPage, data=module, module=module, layout=layout, children=children, label=title))

        assert module.__file__ is not None
        reload.reloader.watcher.add_file(module.__file__)
        for info in pkgutil.iter_modules([str(Path(module.__file__).parent)]):
            submod = importlib.import_module(module.__name__ + f".{info.name}")
            title = get_title(submod)

            if info.ispkg:
                route = solara.Route(info.name, component=RenderPage, children=generate_routes(submod), module=submod, layout=None, label=title)
                # skip empty subpackages
                if len(route.children) == 0:
                    continue
            else:
                # skip empty modules
                if get_renderable(submod) is None:
                    continue
                children = getattr(submod, "routes", [])
                module_layout = getattr(submod, "Layout", None)
                route = solara.Route(info.name, component=RenderPage, module=submod, layout=module_layout, children=children, label=title)
            routes.append(route)
        if route_order:
            lookup = {k.path: k for k in routes}
            for k in route_order:
                if k not in lookup:
                    raise KeyError(f"Route {k!r} listen in route_order not found in {module}")
            routes = [lookup[k] for k in route_order]
            if set(lookup) - set(route_order):
                raise KeyError(f"Some routes are not in route_order: {set(lookup) - set(route_order)}")

    else:
        # single module, single route
        return [solara.Route(path="/", component=RenderPage, data=None, module=module, label=get_title(module))]

    return routes


def generate_routes_directory(path: Path) -> List[solara.Route]:
    subpaths = list(sorted(path.iterdir()))
    routes = []
    first = True
    has_index = len([k for k in subpaths if k.name == "__init__"]) > 0
    suffixes = [".py", ".ipynb", ".md"]
    init = path / "__init__.py"
    layout = None
    if init.exists():
        init_module = source_to_module(init)
        layout = getattr(init_module, "Layout", None)

    for subpath in subpaths:
        # only handle directories and recognized file types
        if not (subpath.is_dir() or subpath.suffix in suffixes):
            continue
        if subpath.stem.startswith("_") or subpath.stem.startswith("."):
            continue
        name = subpath.stem
        match = re.match("([0-9\\-_ ]*)(.*)", name)
        if match:
            _prefix, name = match.groups()
        title_parts = re.split("[\\-_ ]+", name)
        title = " ".join(k.title() for k in title_parts)
        if not has_index and first:
            route_path = "/"
        else:
            route_path = "-".join([k.lower() for k in title_parts])
        # used as a 'sentinel' to find the deepest level of the route tree we need to render in 'RenderPage'
        component = RenderPage
        children = []
        module: Optional[ModuleType] = None
        data: Any = None
        module_layout = layout if first else None
        if subpath.suffix == ".md":
            data = subpath
            reload.reloader.watcher.add_file(subpath)
        elif subpath.is_dir():
            children = generate_routes_directory(subpath)
        else:
            reload.reloader.watcher.add_file(subpath)
            module = source_to_module(subpath)
            children = getattr(module, "routes", children)
            module_layout = getattr(module, "Layout", module_layout)
        first = False
        route = solara.Route(route_path, component=component, module=module, label=title, children=children, data=data, layout=module_layout)
        routes.append(route)
    return routes
