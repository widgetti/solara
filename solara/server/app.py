import dataclasses
import importlib.util
import logging
import os
import pickle
import sys
import threading
import traceback
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, cast

import IPython.display
import ipywidgets as widgets
import reacton
from ipywidgets import DOMWidget, Widget
from reacton.core import Element, render

import solara

from . import kernel, reload, settings, websocket
from .kernel import Kernel, WebsocketStreamWrapper
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
            context = get_current_context()
        except RuntimeError:
            context = None
        if context is not None:
            raise RuntimeError(f"We should not have an existing Solara app context when running an app for the first time: {context}")
        app_context = create_dummy_context()
        with app_context:
            app = self._execute()

        self._first_execute_app = app
        app_context.close()

    def _execute(self):
        logger.info("Executing %s", self.name)
        app = None
        local_scope = {
            "display": IPython.display.display,
            "__name__": "__main__",
            "__file__": str(self.path),
        }
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
        elif self.name.endswith(".py"):
            self.type = AppType.SCRIPT
            add_path()
            local_scope["__name__"] = "__main__"
            # manually add the script to the watcher
            reload.reloader.watcher.add_file(self.path)
            self.directory = self.path.parent.resolve()
            with reload.reloader.watch():
                routes = [solara.autorouting._generate_route_path(self.path, first=True)]

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
        context_values = list(contexts.values())
        contexts.clear()
        for context in context_values:
            context.close()

    def run(self):
        if reload.reloader.requires_reload:
            with thread_lock:
                if reload.reloader.requires_reload:
                    self._first_execute_app = self._execute()
        return self._first_execute_app

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
            # TODO: clearing the type_counter is a bit of a hack
            # and we should introduce reload 'hooks', so there is
            # less interdependency between modules
            import solara.lab.toestand

            solara.lab.toestand.ConnectionStore._type_counter.clear()

            context_values = list(contexts.values())
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


@dataclasses.dataclass
class AppContext:
    id: str
    kernel: kernel.Kernel
    control_sockets: List[WebSocket] = dataclasses.field(default_factory=list)
    # this is the 'private' version of the normally global ipywidgets.Widgets.widget dict
    # see patch.py
    widgets: Dict[str, Widget] = dataclasses.field(default_factory=dict)
    # same, for ipyvue templates
    # see patch.py
    templates: Dict[str, Widget] = dataclasses.field(default_factory=dict)
    user_dicts: Dict[str, Dict] = dataclasses.field(default_factory=dict)
    # anything we need to attach to the context
    # e.g. for a react app the render context, so that we can store/restore the state
    app_object: Optional[Any] = None
    reload: Callable = lambda: None
    state: Any = None
    container: Optional[DOMWidget] = None

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
                    try:
                        self.app_object.close()
                    except Exception as e:
                        logger.exception("Could not close render context: %s", e)
                        # we want to continue, so we at least close all widgets
            widgets.Widget.close_all()
            # what if we reference each other
            # import gc
            # gc.collect()
        if self.id in contexts:
            del contexts[self.id]

    def _state_reset(self):
        state_directory = Path(".") / "states"
        state_directory.mkdir(exist_ok=True)
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


def create_dummy_context():
    from . import kernel

    app_context = AppContext(
        id="dummy",
        kernel=kernel.Kernel(),
    )
    return app_context


def get_current_thread_key() -> str:
    thread = threading.currentThread()
    return get_thread_key(thread)


def get_thread_key(thread: threading.Thread) -> str:
    thread_key = thread._name + str(thread._ident)  # type: ignore
    return thread_key


def set_context_for_thread(context: AppContext, thread: threading.Thread):
    key = get_thread_key(thread)
    current_context[key] = context


def has_current_context() -> bool:
    thread_key = get_current_thread_key()
    return (thread_key in current_context) and (current_context[thread_key] is not None)


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


def set_current_context(context: Optional[AppContext]):
    thread_key = get_current_thread_key()
    current_context[thread_key] = context


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

    context = get_current_context()
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
    context = get_current_context()
    container = context.container
    assert container is not None
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


from . import patch  # noqa

patch.patch()
# the default app (used in solara-server)
if "SOLARA_APP" in os.environ:
    with pdb_guard():
        apps["__default__"] = AppScript(os.environ.get("SOLARA_APP", "solara.website.pages:Page"))
