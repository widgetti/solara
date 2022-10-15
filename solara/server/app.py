import dataclasses
import importlib.util
import logging
import os
import pdb
import pickle
import sys
import threading
import traceback
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, cast

import ipywidgets as widgets
import reacton
from reacton.core import Element, render

import solara

from ..util import cwd
from . import kernel, reload, settings, websocket
from .kernel import Kernel, WebsocketStreamWrapper
from .utils import nested_get

WebSocket = Any
apps: Dict[str, "AppScript"] = {}
thread_lock = threading.Lock()

logger = logging.getLogger("solara.server.app")
state_directory = Path(".") / "states"
state_directory.mkdir(exist_ok=True)


class AppType(str, Enum):
    SCRIPT = "script"
    NOTEBOOK = "notebook"
    MODULE = "module"
    DIRECTORY = "directory"


class AppScript:
    def __init__(self, name, default_app_name="Page"):
        self.fullname = name
        if reload.reloader.on_change:
            raise RuntimeError("Previous reloader still had a on_change attached, no cleanup?")
        reload.reloader.on_change = self.on_file_change

        self.app_name = default_app_name
        if ":" in self.fullname:
            self.name, self.app_name = self.fullname.split(":")
        else:
            self.name = name
        self.path: Path = Path(self.name)
        if self.path.is_dir():
            self.type = AppType.DIRECTORY
            self.directory = self.path
        elif self.name.endswith(".py"):
            self.type = AppType.SCRIPT
            # manually add the script to the watcher
            reload.reloader.watcher.add_file(self.path)
            self.directory = self.path.parent
        elif self.name.endswith(".ipynb"):
            self.type = AppType.NOTEBOOK
            # manually add the notebook to the watcher
            reload.reloader.watcher.add_file(self.path)
            self.directory = self.path.parent
        else:
            # the module itself will be added by reloader
            # automatically
            with reload.reloader.watch():
                self.type = AppType.MODULE
                spec = importlib.util.find_spec(self.name)
                if spec is None:
                    raise ImportError(f"Module {self.name} cannot be found")
                assert spec is not None
                if spec.origin is None:
                    raise ImportError(f"Module {self.name} cannot be found, or is a namespace package")
                assert spec.origin is not None
                self.path = Path(spec.origin)
                self.directory = self.path.parent

        # this is not expected for modules, similar to `python script.py and python -m package.mymodule`
        if self.type in [AppType.SCRIPT, AppType.NOTEBOOK]:
            working_directory = str(self.path.parent)
            if working_directory not in sys.path:
                sys.path.insert(0, working_directory)

        # this might be useful for development
        # but requires reloading of react in solara iself
        # for name, module in sys.modules.items():
        #     if name.startswith("reacton"):
        #         file = inspect.getfile(module)
        #         self.watcher.add_file(file)

        # cgi vars: https://datatracker.ietf.org/doc/html/rfc3875
        os.environ["SCRIPT_NAME"] = self.name
        os.environ["PATH_TRANSLATED"] = str(self.path.resolve())

    def close(self):
        reload.reloader.on_change = None
        context_values = list(contexts.values())
        contexts.clear()
        for context in context_values:
            context.close()

    def run(self):
        with reload.reloader.watch():
            return self._run()

    def _run(self):
        context = get_current_context()
        local_scope = {"display": context.display, "__name__": "__main__", "__file__": str(self.path)}
        ignore = list(local_scope)
        routes: Optional[List[solara.Route]] = None
        if self.type == AppType.DIRECTORY:
            routes = solara.generate_routes_directory(self.path)
            app = solara.RenderPage()
            return app, routes
        elif self.type == AppType.SCRIPT:
            with open(self.path) as f:
                ast = compile(f.read(), self.path, "exec")
                exec(ast, local_scope)
            app = nested_get(local_scope, self.app_name)
            routes = cast(Optional[List[solara.Route]], local_scope.get("routes"))
        elif self.type == AppType.NOTEBOOK:
            import nbformat

            nb: nbformat.NotebookNode = nbformat.read(self.path, 4)
            with cwd(Path(self.path).parent):
                for cell_index, cell in enumerate(nb.cells):
                    cell_index += 1  # used 1 based
                    if cell.cell_type == "code":
                        source = cell.source
                        cell_path = f"{self.path} input cell {cell_index}"
                        ast = compile(source, cell_path, "exec")
                        exec(ast, local_scope)
            app = nested_get(local_scope, self.app_name)
            routes = cast(Optional[List[solara.Route]], local_scope.get("routes"))
        elif self.type == AppType.MODULE:
            mod = importlib.import_module(self.name)

            local_scope = mod.__dict__
            if not hasattr(mod, "routes"):
                if self.app_name == "Page":
                    routes = solara.generate_routes(mod)
                    app = solara.RenderPage()
                else:
                    app = nested_get(local_scope, self.app_name)
            else:
                routes = mod.routes
                app = nested_get(local_scope, self.app_name)
                if app is None:
                    app = solara.autorouting.RenderPage()
        else:
            raise ValueError(self.type)

        if app is None:
            # workaround for backward compatibility
            app = local_scope.get("app")
        if app is None:
            import difflib

            options = [k for k in list(local_scope) if k not in ignore and not k.startswith("_")]
            matches = difflib.get_close_matches(self.app_name, options)
            msg = f"No object with name {self.app_name} found for {self.name} at {self.path}."
            if matches:
                msg += " Did you mean: " + " or ".join(map(repr, matches))
            else:
                msg += " We did find: " + " or ".join(map(repr, options))
            raise NameError(msg)
        if routes is None:
            routes = [solara.Route("/")]
        return app, routes

    def on_file_change(self, name):
        path = Path(name)
        if path.suffix == ".vue":
            logger.info("Vue file changed: %s", name)
            template_content = path.read_text()
            for context in list(contexts.values()):
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
            context_values = list(contexts.values())
            # save states into the context so the hot reload will
            # keep the same state
            for context in context_values:
                render_context = cast(reacton.core._RenderContext, context.app_object)
                if render_context:
                    context.state = render_context.state_get()

            # ask all contexts/users to reload
            for context in context_values:
                with context:
                    context.reload()


# the default app (used in solara-server)
apps["__default__"] = AppScript(os.environ.get("SOLARA_APP", "solara.website.pages:Page"))


@dataclasses.dataclass
class AppContext:
    id: str
    kernel: kernel.Kernel
    control_sockets: List[WebSocket]
    # this is the 'private' version of the normally global ipywidgets.Widgets.widget dict
    # see patch.py
    widgets: Dict[str, widgets.Widget]
    # same, for ipyvue templates
    # see patch.py
    templates: Dict[str, widgets.Widget]
    user_dicts: Dict[str, Dict] = dataclasses.field(default_factory=dict)
    # anything we need to attach to the context
    # e.g. for a react app the render context, so that we can store/restore the state
    app_object: Optional[Any] = None
    reload: Callable = lambda: None
    state: Any = None
    container: Optional[widgets.DOMWidget] = None

    def display(self, *args):
        print(args)  # noqa

    def __enter__(self):
        key = get_current_thread_key()
        current_context[key] = self

    def __exit__(self, *args):
        key = get_current_thread_key()
        current_context[key] = None

    def close(self):
        with self:
            if self.app_object is not None:
                if isinstance(self.app_object, reacton.core._RenderContext):
                    self.app_object.close()
            import solara.server.patch

            assert isinstance(widgets.Widget.widgets, solara.server.patch.context_dict_widgets), f"Unexpected widget dict type: {type(widgets.Widget.widgets)}"
            assert widgets.Widget.widgets._get_context_dict() is self.widgets
            widgets.Widget.close_all()
            # what if we reference eachother
            # import gc
            # gc.collect()
        if self.id in contexts:
            del contexts[self.id]

    def _state_reset(self):
        path = state_directory / f"{self.id}.pickle"
        path = path.absolute()
        try:
            path.unlink()
        except:  # noqa
            pass
        del contexts[self.id]
        key = get_current_thread_key()
        del current_context[key]

    def state_save(self, state_directory: os.PathLike):
        path = Path(state_directory) / f"{self.id}.pickle"
        render_context = self.app_object
        if render_context is not None:
            render_context = cast(reacton.core._RenderContext, render_context)
            state = render_context.state_get()
            with path.open("wb") as f:
                logger.debug("State: %r", state)
                pickle.dump(state, f)


contexts: Dict[str, AppContext] = {}
# maps from thread key to AppContext, if AppContext is None, it exists, but is not set as current
current_context: Dict[str, Optional[AppContext]] = {}


def get_current_thread_key() -> str:
    thread = threading.currentThread()
    return get_thread_key(thread)


def get_thread_key(thread: threading.Thread) -> str:
    thread_key = thread._name + str(thread._ident)  # type: ignore
    return thread_key


def set_context_for_thread(context: AppContext, thread: threading.Thread):
    key = get_thread_key(thread)
    contexts[key] = context
    current_context[key] = context


def get_current_context() -> AppContext:
    thread_key = get_current_thread_key()
    if thread_key not in current_context:
        raise RuntimeError(
            f"Tried to get the current context for thread {thread_key}, but no known context found. This might be a bug in Solara. "
            f"(known contexts: {list(current_context.keys())}"
        )
    context = current_context[thread_key]
    if context is None:
        raise RuntimeError(
            f"Tried to get the current context for thread {thread_key!r}, although the context is know, it was not set for this thread. "
            + "This might be a bug in Solara."
        )
    return context


def _run_app(app_state, app_script: AppScript, pathname: str, render_context: reacton.core._RenderContext = None):

    # app.signal_hook_install()
    main_object, routes = app_script.run()

    context = get_current_context()
    container = context.container
    if isinstance(main_object, widgets.Widget):
        return main_object, render_context
    elif isinstance(main_object, Element) or isinstance(main_object, reacton.core.Component):
        if isinstance(main_object, Element):
            children = [main_object]
        else:
            children = [main_object()]
        solara_context = solara.RoutingProvider(children=children, routes=routes, pathname=pathname)
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
    context = get_current_context()
    container = context.container
    assert container is not None
    try:
        render_context = context.app_object
        with context:
            with reload.reloader.watch():
                while True:
                    # reloading might take in extra dependencies, so the reload happens first
                    if reload.reloader.requires_reload:
                        reload.reloader.reload()
                    # reload before starting app, because we may load state using pickle
                    # if we do that before reloading, the classes are not compatible:
                    app_state = app_state_initial
                    # e.g.: _pickle.PicklingError: Can't pickle <class 'testapp.Clicks'>: it's not the same object as testapp.Clicks
                    try:
                        widget, render_context = _run_app(app_state, app_script, pathname, render_context=render_context)
                        if render_context is None:
                            context.container.children = [widget]
                    except Exception:
                        if settings.main.use_pdb:
                            logger.exception("Exception, will be handled by debugger")
                            pdb.post_mortem()
                        raise

                    if render_context:
                        context.app_object = render_context
                    if not reload.reloader.requires_reload:
                        break

    except BaseException as e:
        error = ""
        error = "".join(traceback.format_exception(None, e, e.__traceback__))
        print(error, file=sys.stdout, flush=True)  # noqa
        # widget = widgets.Label(value="Error, see server logs")
        import html

        error = html.escape(error)
        with context:
            widget = widgets.HTML(f"<pre>{error}</pre>")
            container.children = [widget]


def solara_comm_target(comm, msg_first):
    app: Optional[AppScript] = None

    def on_msg(msg):
        nonlocal app
        data = msg["content"]["data"]
        method = data["method"]
        if method == "run":
            path = data.get("path", "")
            app_name = data.get("appName") or "__default__"
            app = apps[app_name]
            context = get_current_context()
            import ipyvuetify

            container = ipyvuetify.Html(tag="div")
            context.container = container
            with context:
                load_app_widget(None, app, path)
                comm.send({"method": "finished", "widget_id": context.container._model_id})
        elif method == "check":
            context = get_current_context()
        elif method == "reload":
            assert app is not None
            context = get_current_context()
            path = data.get("path", "")
            with context:
                load_app_widget(context.state, app, path)
                comm.send({"method": "finished"})

    comm.on_msg(on_msg)

    def reload():
        # we don't reload the app ourself, we send a message to the client
        # this ensures that we don't run code of any client that for some reason is connected
        # but not working anymore. And it indirectly passes a message from the current thread
        # (which is that of the Reloader/watchdog), to the thread of the client
        logger.debug(f"Send reload to client: {context.id}")
        comm.send({"method": "reload"})

    context = get_current_context()
    context.reload = reload


def register_solara_comm_target(kernel: Kernel):
    kernel.comm_manager.register_target("solara.control", solara_comm_target)


def initialize_virtual_kernel(context_id: str, websocket: websocket.WebsocketWrapper):
    kernel = Kernel()
    logger.info("new virtual kernel: %s", context_id)
    context = contexts[context_id] = AppContext(id=context_id, kernel=kernel, control_sockets=[], widgets={}, templates={})
    with context:
        widgets.register_comm_target(kernel)
        register_solara_comm_target(kernel)
        assert kernel is Kernel.instance()
        kernel.shell_stream = WebsocketStreamWrapper(websocket, "shell")
        kernel.control_stream = WebsocketStreamWrapper(websocket, "control")
        kernel.session.websockets.add(websocket)
