import contextlib
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, TypeVar

import jinja2
import solara

from . import app, settings, websocket
from .app import initialize_virtual_kernel
from .kernel import Kernel, deserialize_binary_message

COOKIE_KEY_SESSION_ID = "solara-session-id"

T = TypeVar("T")


directory = Path(__file__).parent
template_name = "index.html.j2"

# first look at the project directory, then the builtin solara directory
jinja_loader = jinja2.FileSystemLoader([app.apps["__default__"].directory.parent / "templates", str(directory / "templates")])
jinja_env = jinja2.Environment(loader=jinja_loader, autoescape=True)
logger = logging.getLogger("solara.server.server")
nbextensions_ignorelist = [
    "jupytext/index",
    "nbextensions_configurator/config_menu/main",
    "jupytext/index",
    "nbdime/index",
    "voila/extension",
    "contrib_nbextensions_help_item/main",
    "execute_time/ExecuteTime",
    "dominocode/extension",
    "low-code-assistant/extension",
    "jupyter-js/extension",
    "jupyter-js-widgets/extension",
]


async def app_loop(ws: websocket.WebsocketWrapper, session_id: str, connection_id: str):
    initialize_virtual_kernel(connection_id, ws)
    context = app.contexts.get(connection_id)
    if context is None:
        logging.warning("invalid context id: %r", connection_id)
        # to avoid very fast reconnects (we are in a thread anyway)
        time.sleep(0.5)
        return

    if settings.main.tracer:
        import viztracer

        output_file = f"viztracer-{connection_id}.html"
        run_context = viztracer.VizTracer(output_file=output_file, max_stack_depth=10)
        logger.warning(f"Running with tracer: {output_file}")
    else:
        run_context = contextlib.nullcontext()

    kernel = context.kernel
    with run_context:
        while True:
            try:
                message = ws.receive()
            except websocket.WebSocketDisconnect:
                logger.debug("Disconnected")
                return
            t0 = time.time()
            if isinstance(message, str):
                msg = json.loads(message)
            else:
                msg = deserialize_binary_message(message)
            t1 = time.time()
            with context:
                process_kernel_messages(kernel, msg)
                t2 = time.time()
                if settings.main.timing:
                    print(f"timing: total={t2-t0:.3f}s, deserialize={t1-t0:.3f}s, kernel={t2-t1:.3f}s")  # noqa: T201


def process_kernel_messages(kernel: Kernel, msg: Dict):
    session = kernel.session
    comm_manager = kernel.comm_manager

    def send_status(status, parent):
        session.send(
            kernel.iopub_socket,
            "status",
            {"execution_state": status},
            parent=parent,
            ident=None,
        )

    @contextlib.contextmanager
    def busy_idle(parent):
        send_status("busy", parent=parent)
        try:
            yield
        finally:
            send_status("idle", parent=parent)

    msg_type = msg["header"]["msg_type"]
    kernel.set_parent(None, msg["header"], msg["channel"])
    if msg_type == "kernel_info_request":
        content = {
            "status": "ok",
            "protocol_version": "5.3",
            "implementation": Kernel.implementation,
            "implementation_version": Kernel.implementation_version,
            "language_info": {},
            "banner": Kernel.banner,
            "help_links": [],
        }
        with busy_idle(msg["header"]):
            msg = kernel.session.send(kernel.shell_stream, "kernel_info_reply", content, msg["header"], None)
    elif msg_type in ["comm_open", "comm_msg", "comm_close"]:
        with busy_idle(msg["header"]):
            getattr(comm_manager, msg_type)(kernel.shell_stream, None, msg)
    elif msg_type in ["comm_info_request"]:
        content = msg["content"]
        target_name = msg.get("target_name", None)

        comms = {k: dict(target_name=v.target_name) for (k, v) in comm_manager.comms.items() if v.target_name == target_name or target_name is None}
        reply_content = dict(comms=comms, status="ok")
        with busy_idle(msg["header"]):
            msg = session.send(kernel.shell_stream, "comm_info_reply", reply_content, msg["header"], None)
    else:
        logger.error("Unsupported msg with msg_type %r", msg_type)


def read_root(base_url: str = "", render_kwargs={}, use_nbextensions=True):
    if use_nbextensions:
        nbextensions = get_nbextensions()
    else:
        nbextensions = []

    resources = {
        "theme": "light",
        "nbextensions": nbextensions,
    }
    template: jinja2.Template = jinja_env.get_template(template_name)
    render_settings = {
        "base_url": base_url,
        "resources": resources,
        "theme": settings.theme.dict(),
        "production": settings.main.mode == "production",
        **render_kwargs,
    }
    logger.debug("Render setting for template: %r", render_settings)
    response = template.render(**render_settings)
    return response


def find_prefixed_directory(path):
    prefixes = [sys.prefix, os.path.expanduser("~/.local")]
    for prefix in prefixes:
        directory = f"{prefix}{path}"
        if Path(directory).exists():
            return directory
    else:
        raise RuntimeError(f"{path} not found at prefixes: {prefixes}")


@solara.memoize()
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


@solara.memoize()
def get_nbextensions() -> List[str]:
    from jupyter_core.paths import jupyter_config_path

    read_config_path = [os.path.join(p, "serverconfig") for p in jupyter_config_path()]
    read_config_path += [os.path.join(p, "nbconfig") for p in jupyter_config_path()]
    # import inline since we don't want this dep for pyiodide
    from jupyter_server.services.config import ConfigManager

    config_manager = ConfigManager(read_config_path=read_config_path)
    notebook_config = config_manager.get("notebook")
    # except for the widget extension itself, since Voilà has its own
    load_extensions = notebook_config.get("load_extensions", {})
    if "jupyter-js-widgets/extension" in load_extensions:
        load_extensions["jupyter-js-widgets/extension"] = False
    if "voila/extension" in load_extensions:
        load_extensions["voila/extension"] = False
    if "voila/extension" in load_extensions:
        load_extensions["voila/extension"] = False
    directories = get_nbextensions_directories()

    def exists(name):
        for directory in directories:
            if (directory / (name + ".js")).exists():
                return True
        logger.error(f"nbextension {name} not found")
        return False

    nbextensions = [name for name, enabled in load_extensions.items() if enabled and (name not in nbextensions_ignorelist) and exists(name)]
    return nbextensions


if "pyodide" not in sys.modules:
    nbextensions_directories = get_nbextensions_directories()
    nbconvert_static = find_prefixed_directory("/share/jupyter/nbconvert/templates/lab/static")
    solara_static = Path(__file__).parent / "static"
