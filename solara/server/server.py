import json
import logging
import os
import pdb
import sys
import time
import traceback
from pathlib import Path
from typing import List, Optional
from uuid import uuid4

import ipywidgets as widgets
import jinja2
import react_ipywidgets
from jupyter_core.paths import jupyter_config_path
from react_ipywidgets.core import Element, render

from . import app, reload, settings, websocket
from .app import AppContext, AppScript
from .kernel import BytesWrap, Kernel, WebsocketStreamWrapper

directory = Path(__file__).parent
template_name = "solara.html.j2"

jinja_loader = jinja2.FileSystemLoader(str(directory / "templates"))
jinja_env = jinja2.Environment(loader=jinja_loader, autoescape=True)
solara_app = AppScript(os.environ.get("SOLARA_APP", "solara.examples:app"))
logger = logging.getLogger("solara.server.server")


async def app_loop(ws: websocket.WebsocketWrapper, context_id: Optional[str]):
    if context_id is None:
        logging.warning(f"no context id cookie set ({app.COOKIE_KEY_CONTEXT_ID})")
        # to avoid very fast reconnects (we are in a thread anyway)
        time.sleep(0.5)
        return
    context = app.contexts.get(context_id)
    if context is None:
        logging.warning("invalid context id: %r", context_id)
        # to avoid very fast reconnects (we are in a thread anyway)
        time.sleep(0.5)
        return

    kernel = context.kernel
    kernel.shell_stream = WebsocketStreamWrapper(ws, "shell")
    kernel.control_stream = WebsocketStreamWrapper(ws, "control")

    # should we use excepthook ?
    kernel.session.websockets.add(ws)
    if True:
        while True:
            try:
                message = ws.receive()
            except websocket.WebSocketDisconnect:
                logger.debug("Disconnected")
                return
            if isinstance(message, str):
                msg = json.loads(message)
            else:
                from jupyter_server.base.zmqhandlers import deserialize_binary_message

                msg = deserialize_binary_message(message)

            msg_serialized = kernel.session.serialize(msg)
            channel = msg["channel"]
            if channel == "shell":
                msg = [BytesWrap(k) for k in msg_serialized]
                with context:
                    await kernel.dispatch_shell(msg)
            else:
                print("unknown channel", msg["channel"])


def control_loop(ws: websocket.WebsocketWrapper, context_id: Optional[str]):
    if context_id is None:
        ws.send_json({"type": "reload", "reason": "no context id found in cookie"})
        ws.close()
        return
    context = app.contexts.get(context_id)
    if context is None:
        ws.send_json({"type": "reload", "reason": "context does not exist (server reload?)"})
    if context:
        app.contexts[context_id].control_sockets.append(ws)
    ok = True

    while ok:
        try:
            msg = ws.receive_json()
            if msg["type"] == "state_reset":
                logger.info(f"reset state for context {context_id}")
                if context:
                    context.state_reset()
                ws.send_json({"type": "reload", "reason": "context id does not exist (server reload?)"})
            else:
                logger.error("Unknown msg: {msg}")
        except Exception:
            context = app.contexts.get(context_id)
            if context:
                try:
                    context.control_sockets.remove(ws)
                except ValueError:
                    pass  # could be removed from kernel.py
            ok = False
            # make sure it is closed
            try:
                ws.close()
            except:  # noqa
                pass


def run_app(app_state):
    # app.signal_hook_install()
    main_object = solara_app.run()

    render_context = None

    if isinstance(main_object, widgets.Widget):
        return main_object, render_context
    elif isinstance(main_object, Element):
        # container = widgets.VBox()
        import ipyvuetify

        container = ipyvuetify.Html(tag="div")
        # container = ipyvuetify.Html(tag="div")
        # support older versions of react
        result = render(main_object, container, handle_error=False, initial_state=app_state)
        if isinstance(result, tuple):
            container, render_context = result
        else:
            render_context = result
        return container, render_context
    else:
        raise ValueError(f"Main object (with name {solara_app.app_name} in {solara_app.path}) is not a Widget or Element, but {type(main_object)}")


async def read_root(context_id: Optional[str], base_url: str = ""):
    # context_id = None
    if context_id is None or context_id not in app.contexts:
        kernel = Kernel()
        if context_id is None:
            context_id = str(uuid4())
        context = app.contexts[context_id] = AppContext(id=context_id, kernel=kernel, control_sockets=[], widgets={}, templates={})
        with context:
            widgets.register_comm_target(kernel)
            assert kernel is Kernel.instance()
        try:
            with context:
                with reload.reloader.watch():
                    while True:
                        # reloading might take in extra dependencies, so the reload happens first
                        if reload.reloader.requires_reload:
                            reload.reloader.reload()
                        # reload before starting app, because we may load state using pickle
                        # if we do that before reloading, the classes are not compatible:
                        # e.g.: _pickle.PicklingError: Can't pickle <class 'testapp.Clicks'>: it's not the same object as testapp.Clicks
                        try:
                            app_state = app.state_load(context_id)
                            logger.debug("Loaded state: %r", app_state)
                        except Exception:
                            app_state = None
                        try:
                            widget, render_context = run_app(app_state)
                        except Exception:
                            if settings.main.use_pdb:
                                logger.exception("Exception, will be handled by debugger")
                                pdb.post_mortem()
                            raise

                        if render_context:
                            context.app_object = render_context
                        if not reload.reloader.requires_reload:
                            break

        except react_ipywidgets.core.ComponentCreateError as e:
            from rich.console import Console

            console = Console(record=True)
            console.print(e.rich_traceback)
            error = console.export_html()
            widget = widgets.HTML(f"<pre>{error}</pre>")
            # raise
        except Exception as e:
            error = ""
            error = "".join(traceback.format_exception(None, e, e.__traceback__))
            print(error, file=sys.stdout, flush=True)
            # widget = widgets.Label(value="Error, see server logs")
            import html

            error = html.escape(error)
            with context:
                widget = widgets.HTML(f"<pre>{error}</pre>")
            # raise
        context.widgets["content"] = widget
    else:
        context = app.contexts[context_id]

    model_id = context.widgets["content"].model_id

    read_config_path = [os.path.join(p, "serverconfig") for p in jupyter_config_path()]
    read_config_path += [os.path.join(p, "nbconfig") for p in jupyter_config_path()]
    # import inline since we don't want this dep for pyiodide
    from jupyter_server.services.config import ConfigManager

    config_manager = ConfigManager(read_config_path=read_config_path)
    enable_nbextensions = True
    if enable_nbextensions:
        notebook_config = config_manager.get("notebook")
        # except for the widget extension itself, since Voilà has its own
        load_extensions = notebook_config.get("load_extensions", {})
        if "jupyter-js-widgets/extension" in load_extensions:
            load_extensions["jupyter-js-widgets/extension"] = False
        if "voila/extension" in load_extensions:
            load_extensions["voila/extension"] = False
        ignorelist = [
            "jupytext/index",
            "nbextensions_configurator/config_menu/main",
            "jupytext/index",
            "nbdime/index",
            "voila/extension",
            "contrib_nbextensions_help_item/main",
            "execute_time/ExecuteTime",
        ]
        nbextensions = [name for name, enabled in load_extensions.items() if enabled and name not in ignorelist]
    else:
        nbextensions = []

    resources = {
        "theme": "light",
        "nbextensions": nbextensions,
    }
    template: jinja2.Template = jinja_env.get_template(template_name)
    render_settings = {
        "model_id": model_id,
        "base_url": base_url,
        "resources": resources,
        "theme": settings.theme.dict(),
    }
    logger.info("Render setting for template: %r", render_settings)
    response = template.render(**render_settings)
    return response, context_id


def find_prefixed_directory(path):
    prefixes = [sys.prefix, os.path.expanduser("~/.local")]
    for prefix in prefixes:
        directory = f"{prefix}{path}"
        if Path(directory).exists():
            return directory
    else:
        raise RuntimeError(f"{path} not found at prefixes: {prefixes}")


def get_nbextensions_directories() -> List[Path]:
    from jupyter_core.paths import jupyter_path

    all_nb_directories = jupyter_path("nbextensions")
    # FIXME: remove IPython nbextensions path after a migration period
    try:
        from IPython.paths import get_ipython_dir
    except ImportError:
        pass
    else:
        all_nb_directories.append(Path(get_ipython_dir()) / "nbextensions")
    return [Path(k) for k in all_nb_directories]


nbextensions_directories = get_nbextensions_directories()
voila_static = find_prefixed_directory("/share/jupyter/voila/templates/base/static")
nbconvert_static = find_prefixed_directory("/share/jupyter/nbconvert/templates/lab/static")
solara_static = Path(__file__).parent / "static"
