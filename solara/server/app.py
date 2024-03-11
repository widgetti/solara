import importlib.util
import logging
import os
import pickle
import sys
import threading
import traceback
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, cast

import ipywidgets as widgets
import reacton
from reacton.core import Element, render

import solara

from . import kernel_context, patch, reload, settings
from .kernel import Kernel
from .utils import pdb_guard

WebSocket = Any
apps: Dict[str, "AppScript"] = {}
thread_lock = threading.Lock()

logger = logging.getLogger("solara.server.app")

reload.reloader.start()


class AppType(str, Enum):
    SCRIPT = "script"
    NOTEBOOK = "notebook"
    MODULE = "module"
    DIRECTORY = "directory"


def display(*args, **kwargs):
    print("display not implemented", args, kwargs)  # noqa


class AppScript:
    directory: Path
    routes: List[solara.Route]

    def __init__(self, name, default_app_name="Page"):
        self.fullname = name
        if reload.reloader.on_change:
            raise RuntimeError("Previous reloader still had a on_change attached, no cleanup?")
        reload.reloader.on_change = self.on_file_change

        self.app_name = default_app_name
        if ":" in self.fullname:
            self.name, self.app_name = self.fullname.rsplit(":", 1)
            if len(self.name) == 1:  # a windows drive letter, restore
                self.name = self.fullname
                self.app_name = default_app_name
        else:
            self.name = name
        self.path: Path = Path(self.name).resolve()
        try:
            context = kernel_context.get_current_context()
        except RuntimeError:
            context = None
        if context is not None:
            raise RuntimeError(f"We should not have an existing Solara app context when running an app for the first time: {context}")
        dummy_kernel_context = kernel_context.create_dummy_context()
        with dummy_kernel_context:
            app = self._execute()

        # We now ran the app, now we can check for patches that require heavy imports
        patch.patch_heavy_imports()

        self._first_execute_app = app
        reload.reloader.root_path = self.directory
        if self.type == AppType.MODULE:
            package_name = self.name.split(".")[0]
            mod = importlib.import_module(package_name)
            if mod.__file__ is not None:
                package_root_path = Path(mod.__file__).parent
                reload.reloader.root_path = package_root_path
        dummy_kernel_context.close()

    def _execute(self):
        logger.info("Executing %s", self.name)
        app = None
        routes: Optional[List[solara.Route]] = None

        def add_path():
            # this is not expected for modules, similar to `python script.py and python -m package.mymodule`
            if self.type in [AppType.SCRIPT, AppType.NOTEBOOK]:
                working_directory = str(self.path.parent)
                if working_directory not in sys.path:
                    sys.path.insert(0, working_directory)

        if self.path.is_dir():
            self.type = AppType.DIRECTORY
            # resolve the directory, because Path("file").parent.parent == "." != ".."
            self.directory = self.path.resolve()
            routes = solara.generate_routes_directory(self.path)

            if any(name for name in sys.modules.keys() if name.startswith(self.name)):
                logger.warn(
                    f"Directory {self.name} is also used as a package. This can cause modules to be loaded twice, and might "
                    "cause unexpected behavior. If you run solara from a different directory (e.g. the parent directory) you "
                    "can avoid this ambiguity."
                )

        elif self.name.endswith(".py"):
            self.type = AppType.SCRIPT
            add_path()
            # manually add the script to the watcher
            reload.reloader.watcher.add_file(self.path)
            self.directory = self.path.parent.resolve()
            initial_namespace = {
                "__name__": "__main__",
            }
            with reload.reloader.watch():
                routes = [solara.autorouting._generate_route_path(self.path, first=True, initial_namespace=initial_namespace)]
        elif self.name.endswith(".ipynb"):
            self.type = AppType.NOTEBOOK
            add_path()
            # manually add the notebook to the watcher
            reload.reloader.watcher.add_file(self.path)
            self.directory = self.path.parent.resolve()
            with reload.reloader.watch():
                routes = [solara.autorouting._generate_route_path(self.path, first=True)]
        else:
            # the module itself will be added by reloader
            # automatically
            with reload.reloader.watch():
                self.type = AppType.MODULE
                try:
                    spec = importlib.util.find_spec(self.name)
                except ValueError:
                    if self.name not in sys.modules:
                        raise ImportError(f"Module {self.name} not found")
                    spec = importlib.util.spec_from_file_location(self.name, sys.modules[self.name].__file__)
                if spec is None:
                    raise ImportError(f"Module {self.name} cannot be found")
                assert spec is not None
                if spec.origin is None:
                    raise ImportError(f"Module {self.name} cannot be found, or is a namespace package")
                assert spec.origin is not None
                self.path = Path(spec.origin)
                self.directory = self.path.parent

                mod = importlib.import_module(self.name)
                routes = solara.generate_routes(mod)

        app = solara.autorouting.RenderPage(self.app_name)
        if not hasattr(routes[0].module, self.app_name) and routes[0].children:
            routes = routes[0].children

        if settings.ssg.build_path is None:
            settings.ssg.build_path = self.directory.parent.resolve() / "build"

        # auto enable search if search.json exists
        search_index_file = self.directory.parent / "assets" / "search.json"
        if search_index_file.exists():
            settings.search.enabled = True

        # this might be useful for development
        # but requires reloading of react in solara itself
        # for name, module in sys.modules.items():
        #     if name.startswith("reacton"):
        #         file = inspect.getfile(module)
        #         self.watcher.add_file(file)

        # cgi vars: https://datatracker.ietf.org/doc/html/rfc3875
        # we cannot set script name, because gunicorn uses it (and will crash)
        # os.environ["SCRIPT_NAME"] = self.name
        os.environ["PATH_TRANSLATED"] = str(self.path.resolve())

        self.routes = routes

        # this might be useful for development
        # but requires reloading of react in solara itself
        # for name, module in sys.modules.items():
        #     if name.startswith("reacton"):
        #         file = inspect.getfile(module)
        #         self.watcher.add_file(file)

        # cgi vars: https://datatracker.ietf.org/doc/html/rfc3875
        # we cannot set script name, because gunicorn uses it (and will crash)
        # os.environ["SCRIPT_NAME"] = self.name
        os.environ["PATH_TRANSLATED"] = str(self.path.resolve())
        return app

    def close(self):
        reload.reloader.on_change = None
        context_values = list(kernel_context.contexts.values())
        kernel_context.contexts.clear()
        for context in context_values:
            context.close()

    def run(self):
        if reload.reloader.requires_reload or self._first_execute_app is None:
            with thread_lock:
                if reload.reloader.requires_reload or self._first_execute_app is None:
                    self._first_execute_app = None
                    self._first_execute_app = self._execute()
                    print("Re-executed app", self.name)  # noqa
                    # We now ran the app again, might contain new imports
                    patch.patch_heavy_imports()

        return self._first_execute_app

    def on_file_change(self, name):
        path = Path(name)
        if path.suffix == ".vue":
            logger.info("Vue file changed: %s", name)
            template_content = path.read_text()
            for context in list(kernel_context.contexts.values()):
                with context:
                    for filepath, widget in context.templates.items():
                        if filepath == str(path):
                            widget.template = template_content
        else:
            logger.info("Reload requires due to change in module: %s", name)
            self.reload()

    def reload(self):
        # if multiple files change in a short time, we want to do this
        # not concurrently. Even better would be to do a debounce?
        with thread_lock:
            # TODO: clearing the type_counter is a bit of a hack
            # and we should introduce reload 'hooks', so there is
            # less interdependency between modules
            import solara.lab.toestand

            solara.lab.toestand.ConnectionStore._type_counter.clear()

            context_values = list(kernel_context.contexts.values())
            # save states into the context so the hot reload will
            # keep the same state
            for context in context_values:
                render_context = cast(reacton.core._RenderContext, context.app_object)
                if render_context:
                    with context:
                        # we save the state for when the app reruns, so we stay in the same state.
                        # (e.g. button clicks, chosen options etc)
                        # for instance a dataframe, needs to be pickled, because after the pandas
                        # module is reloaded, it's a different class type
                        logger.info("pickling state: %s", render_context.state_get())
                        try:
                            context.state = pickle.dumps(render_context.state_get())
                        except Exception as e:
                            logger.warning("Could not pickle state, next render the state will be lost: %s", e)
                        # clear/cleanup the render_context, so during reload we start
                        # from scratch
                        context.app_object = None
                        # we want to reuse the container
                        render_context.container = None
                        try:
                            render_context.close()
                        except Exception as e:
                            logger.exception("Could not close render context: %s", e)

            # ask all contexts/users to reload
            for context in context_values:
                with context:
                    context.reload()


def _run_app(
    app_state,
    app_script: AppScript,
    pathname: str,
    render_context: reacton.core._RenderContext = None,
):
    # app.signal_hook_install()
    main_object = app_script.run()
    app_state = pickle.loads(app_state) if app_state is not None else None
    if app_state:
        logger.info("Restoring state: %r", app_state)

    context = kernel_context.get_current_context()
    container = context.container
    if isinstance(main_object, widgets.Widget):
        return main_object, render_context
    elif isinstance(main_object, Element) or isinstance(main_object, reacton.core.Component):
        if isinstance(main_object, Element):
            children = [main_object]
        else:
            children = [main_object()]
        solara_context = solara.RoutingProvider(children=children, routes=app_script.routes, pathname=pathname)
        if render_context is None:
            result = render(solara_context, container, handle_error=True, initial_state=app_state)
            # support older versions of react
            if isinstance(result, tuple):
                container, render_context = result
            else:
                render_context = result
        else:
            if app_state:
                render_context.state_set(render_context.context_root, app_state)
            result = render_context.render(solara_context)
            container = render_context.container
        # return container, render_context
    else:
        extra = ""
        dotted = []
        for key, value in vars(main_object).items():
            if isinstance(value, (Element, widgets.Widget)):
                dotted.append(f"{app_script.app_name}.{key}")
        if dotted:
            extra = " We did find that sub objects that might work: " + ", ".join(dotted)
        raise ValueError(
            f"Main object (with name {app_script.app_name} in {app_script.path}) is not a Widget, Element or Component, but {type(main_object)}." + extra
        )
    return container, render_context


def load_app_widget(app_state, app_script: AppScript, pathname: str):
    # load the app, and set it at the child of the context's container
    app_state_initial = app_state
    context = kernel_context.get_current_context()
    container = context.container
    assert container is not None
    try:
        import ipyreact

        del ipyreact
    except ModuleNotFoundError:
        pass
    else:
        import solara.server.esm

        # will create widgets, but will clean itself up when the kernel closes
        solara.server.esm.create_modules()
        solara.server.esm.create_import_map()

    try:
        render_context = context.app_object
        app_state = app_state_initial
        with pdb_guard():
            widget, render_context = _run_app(
                app_state,
                app_script,
                pathname,
                render_context=render_context,
            )
            if render_context is None:
                assert context.container is not None
                context.container.children = [widget]

        if render_context:
            context.app_object = render_context

    except BaseException as e:
        error = ""
        error = "".join(traceback.format_exception(None, e, e.__traceback__))
        print(error, file=sys.stdout, flush=True)  # noqa
        # widget = widgets.Label(value="Error, see server logs")
        import html

        error = html.escape(error)
        with context:
            widget = widgets.HTML(f"<pre>{error}</pre>", layout=widgets.Layout(overflow="auto"))
            container.children = [widget]


def load_themes(themes: Dict[str, Dict[str, str]], dark: bool):
    # While these usually gets set from the frontend, in solara (server) we want to know theme information directly at the first
    # render. Also, using the same trait allows us to write code which works on all widgets platforms, instead
    # or using something different when running under solara server
    from solara.lab.components.theming import _set_theme, theme

    _set_theme(themes)
    theme.dark_effective = dark


def solara_comm_target(comm, msg_first):
    app: Optional[AppScript] = None

    def on_msg(msg):
        nonlocal app
        data = msg["content"]["data"]
        method = data["method"]
        if method == "run":
            args = data["args"]
            path = args.get("path", "")
            app_name = args.get("appName") or "__default__"
            app = apps[app_name]
            context = kernel_context.get_current_context()
            import ipyvuetify

            container = ipyvuetify.Html(tag="div")
            context.container = container
            themes = args.get("themes")
            dark = args.get("dark")
            load_themes(themes, dark)
            load_app_widget(None, app, path)
            comm.send({"method": "finished", "widget_id": context.container._model_id})
        elif method == "app-status":
            context = kernel_context.get_current_context()
            # if there is no container, we never ran the app
            if context.container is not None:
                logger.info("app-status check: %s app started", context.id)
                comm.send({"method": "app-status", "started": True})
            else:
                logger.info("app-status check: %s app not started", context.id)
                comm.send({"method": "app-status", "started": False})

        elif method == "reload":
            from solara.lab.components.theming import _get_theme, theme

            assert app is not None
            context = kernel_context.get_current_context()
            path = data.get("path", "")
            current_theme = theme._instance.value
            theme_dict = _get_theme(current_theme)

            with context:
                context.restart()
                load_themes(theme_dict, current_theme.dark_effective)
                load_app_widget(context.state, app, path)
                comm.send({"method": "finished"})
        else:
            logger.error("Unknown comm method called on solara.control comm: %s", method)

    comm.on_msg(on_msg)

    def reload():
        # we don't reload the app ourself, we send a message to the client
        # this ensures that we don't run code of any client that for some reason is connected
        # but not working anymore. And it indirectly passes a message from the current thread
        # (which is that of the Reloader/watchdog), to the thread of the client
        logger.debug(f"Send reload to client: {context.id}")
        comm.send({"method": "reload"})

    context = kernel_context.get_current_context()
    context.reload = reload


def register_solara_comm_target(kernel: Kernel):
    kernel.comm_manager.register_target("solara.control", solara_comm_target)


from . import patch  # noqa

patch.patch()
# the default app (used in solara-server)
if "SOLARA_APP" in os.environ:
    with pdb_guard():
        apps["__default__"] = AppScript(os.environ.get("SOLARA_APP", "solara.website.pages:Page"))
