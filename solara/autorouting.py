import dataclasses
import difflib
import importlib
import inspect
import pkgutil
import re
import warnings
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, Dict, List, Optional, cast

import ipywidgets
import reacton
import reacton.core

import solara
import solara.checks
from solara.alias import rv
from solara.util import cwd, nested_get

autoroute_level_context = solara.create_context(0)
DEBUG = False

solara_root = Path(solara.__file__).parent

DefaultLayout = solara.AppLayout


def source_to_module(path: Path, initial_namespace={}) -> ModuleType:
    fullname = path.stem
    mod = ModuleType(fullname)
    mod.__file__ = str(path)
    mod.__dict__.update(initial_namespace)
    if path.suffix == ".py":
        with open(path, encoding="utf8") as f:
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
            # raise TypeError(f"{f} expected positional argument {param}, but not enough argument supplied")
        annotation = param.annotation
        value = args[i]
        check_optional_types = [str, int, float]
        for check_type in check_optional_types:
            if annotation == Optional[check_type]:
                annotation = check_type
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
    path, set_path = solara.use_state(pathname, key="solara-context-path")
    # TODO: since we provide a cross filter context here, I don't think name `RoutingProvider` is a good name
    # we might want to change/refactor this.
    solara.provide_cross_filter()
    nav = solara.Navigator(location=path, on_location=set_path)
    solara.routing._location_context.provide(solara.routing._Location(path, set_path))
    solara.routing.router_context.provide(solara.routing.Router(path, routes=routes, set_path=set_path))

    def get_nav_widget():
        # not sure why get_widget(nav) does not work
        nav_widget.current = solara.get_widget(main).children[0]  # type: ignore

    import solara.widgets as w

    nav_widget = solara.use_ref(cast(Optional[w.Navigator], None))
    if nav_widget.current:
        nav_widget.current.location = path
    solara.use_effect(get_nav_widget)

    if solara.checks.should_perform_solara_check():
        children = [solara.checks.SolaraCheck(), *children]

    main = solara.VBox(
        children=[
            nav,
            *children,
        ]
    )

    return main


@solara.component
def RenderPage(main_name: str = "Page"):
    """Renders the page that matches the route."""
    level_start = solara.use_route_level()
    router = solara.use_context(solara.routing.router_context)
    # we use these to cache script runs that use regular ipywidgets
    modules = cast(Dict[str, ModuleType], solara.use_memo(dict, dependencies=[]))
    modules_modified_times = solara.use_memo(dict, dependencies=[])

    if len(router.path_routes) <= level_start:
        with solara.VBox() as main:
            solara.Error(f"Page not found: {router.path}, len(router.path_routes)={len(router.path_routes)} <= level_start={level_start}")
            parent = "/" + "/".join(router.parts[:-1])
            with solara.Link(parent):
                solara.Button(f"Go to parent: {parent}", text=True)
            if DEBUG:
                from reacton.core import pp

                from solara.components.captureoutput import CaptureOutput

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
        layouts = [DefaultLayout]
    if route_current.data is None and route_current.module is None and route_current.component is None:
        return solara.Error(f"Page not found: {router.path}, route does not link to a path or module or component")

    def wrap_in_layouts(element: reacton.core.Element, layouts):
        for Layout in reversed(layouts):
            element = Layout(children=[element])
        return element

    def get_args(f):
        if len(router.path_routes) < len(router.parts):
            arg_strings = router.parts[len(router.path_routes) :]
            args = arg_cast(arg_strings, f)
            return args
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
            is_relative = str(path.resolve()).startswith(str(solara_root.resolve()))
            if is_relative:
                # this is now hardcoded to solara only
                url = solara.util.github_edit_url(path)
                with solara.Div(style={"position": "relative"}) as content:
                    with solara.Tooltip("Edit on GitHub"):
                        solara.Button(
                            icon_name="mdi-pencil", icon=True, href=url, target="_blank", style={"position": "absolute", "top": "0px", "right": "0px"}
                        )
                    solara.Markdown(path.read_text(), unsafe_solara_execute=True)
            else:
                content = solara.Markdown(path.read_text(), unsafe_solara_execute=True)

            main = solara.Div(
                classes=["solara-autorouter-content"],
                children=[
                    solara.Title(route_current.label or "No title"),
                    content,
                    navigation,
                ],
            )
            main = wrap_in_layouts(main, layouts)
        else:
            main = solara.Error(f"Suffix {path.suffix} not supported")
    else:
        title = route_current.label or "No title"
        title_element = solara.Title(title)
        module = None
        Page = route_current.component
        # translate the default RenderPage as no value given (None)
        if Page is RenderPage:
            Page = None
        if route_current.module is not None and (Page is None):
            # if not a custom component is given, we try to find a Page component
            # in the module
            assert route_current.module is not None
            module = route_current.module
            namespace = module.__dict__
            Page = nested_get(namespace, main_name, Page)
            if Page is None:
                # app is for backwards compatibility
                Page = namespace.get("page", namespace.get("app", Page))
                Page = nested_get(namespace, main_name, Page)

        if Page is None and route_current.children:
            # we we did not get a component, but we recursively render
            Page = RenderPage
        if isinstance(Page, ipywidgets.Widget):
            # If we have a widget, we need to execute this again for each
            # connection, since we cannot share widgets between connections/users.
            # We also cannot tear them down, so we cache the widget based pages.
            # To support hot reload, we manually need to check the mtimes
            # because the reload support for modules in reloader.py only works
            # for modules.
            if route_current.file is None:
                page = solara.Error(f"{route_current.path} is not associated with a file")
            else:
                assert route_current.file is not None
                if route_current.path not in modules:
                    modules[route_current.path] = source_to_module(route_current.file)
                    modules_modified_times[route_current.path] = route_current.file.stat().st_mtime
                else:
                    if modules_modified_times[route_current.path] != route_current.file.stat().st_mtime:
                        # out of date, 'reload'
                        modules[route_current.path] = source_to_module(route_current.file)
                        modules_modified_times[route_current.path] = route_current.file.stat().st_mtime
                Page = nested_get(modules[route_current.path], main_name, None)
                if Page is None:
                    Page = getattr(modules[route_current.path], "app", None)
                    Page = getattr(modules[route_current.path], "page", Page)
            main = solara.Div(
                classes=["solara-autorouter-content"],
                children=[
                    title_element,
                    Page,
                ],
            )
            main = wrap_in_layouts(main, layouts)
        elif Page is not None:
            if isinstance(Page, reacton.core.ComponentFunction):
                args = get_args(Page)
                page = Page(*args)
            elif isinstance(Page, solara.Element):
                page = Page
            else:
                page = solara.Error(f"{Page} is not a component or element, but {type(Page)}")
            main = solara.Div(
                classes=["solara-autorouter-content"],
                children=[
                    title_element,
                    page,
                ],
            )
            main = wrap_in_layouts(main, layouts)
        else:
            if route_current.module:
                path = route_current.module.__file__
                local_scope = route_current.module.__dict__
                ignore = ["display"]
                options = [k for k in list(local_scope) if k not in ignore and not k.startswith("_")]
                matches = difflib.get_close_matches(main_name, options)
                msg = f"No object with name {main_name} found for {path}"
                if matches:
                    msg += " Did you mean: " + " or ".join(map(repr, matches))
                else:
                    msg += " We did find: " + " or ".join(map(repr, options))
            else:
                msg = f"{module} does not have a Page component or an app element"

            with DefaultLayout() as main:
                solara.Error(msg)
    return main


def get_page(module: ModuleType, required=True):
    page = getattr(module, "Page", None)
    if required and page is None:
        raise NameError(f"No component names 'Page' in module {module}")
    return page


def get_renderable(module: ModuleType, required=False):
    var_names = "app Page page".split()
    for var_name in var_names:
        if not hasattr(module, var_name):
            continue
        entry = getattr(module, var_name)
        return entry
    if required:
        raise NameError(f"No component, element or widget found in module {module} with names: {', '.join(var_names[:-1])} or {var_names[-1]}")


def get_title(module: ModuleType, required=True):
    assert module.__file__ is not None
    name = Path(module.__file__).stem
    if module.__file__.endswith("__init__.py"):
        name = Path(module.__file__).parent.stem
    # if title is a submodule it may shadown the variable in __init__
    # in this case, _title is an escape hatch
    if hasattr(module, "_title") and isinstance(module._title, str):
        title = module._title
    elif hasattr(module, "title") and isinstance(module.title, str):
        title = module.title
    else:
        match = re.match("([0-9\\-_ ]*)(.*)", name)
        if match:
            _prefix, name = match.groups()
        title_parts = re.split("[\\-_ ]+", name)
        title = " ".join(k.title() for k in title_parts)
    return title


def fix_route(route: solara.Route, new_file: Path) -> solara.Route:
    file = route.file or new_file
    children = fix_routes(route.children, new_file) if route.children else []

    return dataclasses.replace(route, file=file, children=children)


def fix_routes(routes: List[solara.Route], new_file: Path):
    new_routes = []
    for route in routes:
        new_routes.append(fix_route(route, new_file))
    return new_routes


def generate_routes(module: ModuleType) -> List[solara.Route]:
    """Generate routes from a module.

    This is a recursive function that will generate routes for all submodules.

    Note this only support .py files, since Markdown files and Jupyter notebook
    files are not Python modules.


    See [our multipage guide](/docs/howto/multipage#as-a-package) for more details.


    """
    from .server import reload

    assert module.__file__ is not None
    routes = []
    file = Path(module.__file__)

    if module.__file__.endswith("__init__.py"):
        if hasattr(module, "routes"):
            # if routes if provided, use them instead of us generating them
            children = getattr(module, "routes")
            children = fix_routes(children, file)
            return children
        route_order = getattr(module, "route_order", None)
        layout = getattr(module, "Layout", None)
        title = get_title(module)
        children = getattr(module, "routes", [])
        if hasattr(module, "Page"):
            routes.append(solara.Route(path="/", component=RenderPage, data=module, module=module, layout=layout, children=children, label=title, file=file))

        assert module.__file__ is not None
        reload.reloader.watcher.add_file(module.__file__)
        for info in pkgutil.iter_modules([str(Path(module.__file__).parent)]):
            submod = importlib.import_module(module.__name__ + f".{info.name}")
            subfile = Path(submod.__file__) if submod.__file__ is not None else None
            title = get_title(submod)

            name = info.name
            # ideally, we do this similar to generate_routes_directory
            # however, this may break things.
            # name = name.replace("_", "-")
            if info.ispkg:
                route = solara.Route(name, component=RenderPage, children=generate_routes(submod), module=submod, layout=None, label=title)
                # skip empty subpackages
                if len(route.children) == 0:
                    continue
            else:
                # skip empty modules
                if get_renderable(submod) is None and not hasattr(submod, "routes"):
                    continue
                children = getattr(submod, "routes", [])
                if subfile:
                    children = fix_routes(children, subfile)
                module_layout = getattr(submod, "Layout", None)
                route = solara.Route(name, component=RenderPage, module=submod, layout=module_layout, children=children, label=title, file=subfile)
            routes.append(route)
        if route_order:
            lookup = {k.path: k for k in routes}
            for k in route_order:
                if k not in lookup:
                    raise KeyError(f"Route {k!r} listen in route_order not found in {module}")
            routes = [lookup[k] for k in route_order]
            if set(lookup) - set(route_order):
                warnings.warn(f"Some routes are not in route_order: {set(lookup) - set(route_order)}")

    else:
        children = getattr(module, "routes", [])
        children = fix_routes(children, file)
        layout = getattr(module, "Layout", None)
        # children = []
        # single module, single route
        return [solara.Route(path="/", component=RenderPage, data=None, module=module, label=get_title(module), layout=layout, children=children, file=file)]

    return routes


def generate_routes_directory(path: Path) -> List[solara.Route]:
    """Generate routes for a directory.

    This is a recursive function that will generate routes for all
    subdirectories and files in the directory. It will skip any
    files or directories that start with an underscore or a dot.

    Markdown files ending in .md will be rendered as markdown.

    Python files ending in .py, or Jupyter notebooks ending in .ipynb
    will be executed and its `Page` component will be rendered.

    Automatic titles will be [generated as explained in the multipage guide](/docs/howto/multipage).

    """

    subpaths = list(sorted(path.iterdir()))
    routes = []
    first = True
    has_index = len([k for k in subpaths if k.name == "__init__"]) > 0
    init = path / "__init__.py"
    layout = None
    if init.exists():
        init_module = source_to_module(init)
        layout = getattr(init_module, "Layout", None)

    suffixes = [".py", ".ipynb", ".md"]
    for subpath in subpaths:
        # only handle directories and recognized file types
        if not (subpath.is_dir() or subpath.suffix in suffixes):
            continue
        if subpath.stem.startswith("_") or subpath.stem.startswith("."):
            continue
        route = _generate_route_path(subpath, layout=layout, first=first, has_index=has_index)
        first = False
        routes.append(route)
    return routes


def _generate_route_path(subpath: Path, layout=None, first=False, has_index=False, initial_namespace={}) -> solara.Route:
    from .server import reload

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
        module = source_to_module(subpath, initial_namespace=initial_namespace)
        title = get_title(module)
        children = getattr(module, "routes", children)
        children = fix_routes(children, subpath)
        module_layout = getattr(module, "Layout", module_layout)
    route = solara.Route(route_path, component=component, module=module, label=title, children=children, data=data, layout=module_layout, file=subpath)
    return route
