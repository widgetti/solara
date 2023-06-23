import contextlib
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, TypeVar

import ipykernel
import ipywidgets
import jinja2
import requests

import solara
import solara.routing

from . import app, settings, websocket
from .app import initialize_virtual_kernel
from .kernel import Kernel, deserialize_binary_message

COOKIE_KEY_SESSION_ID = "solara-session-id"

T = TypeVar("T")


directory = Path(__file__).parent
template_name = "index.html.j2"
ipykernel_major = int(ipykernel.__version__.split(".")[0])
ipywidgets_major = int(ipywidgets.__version__.split(".")[0])
cache_memory = solara.cache.Memory(max_items=128)

# first look at the project directory, then the builtin solara directory


def get_jinja_env(app_name: str) -> jinja2.Environment:
    jinja_loader = jinja2.FileSystemLoader(
        [
            app.apps["__default__"].directory.parent / "templates",
            str(directory / "templates"),
        ]
    )
    jinja_env = jinja2.Environment(loader=jinja_loader, autoescape=True)
    return jinja_env


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
    "domino-code-assist/extension",
    "jupyter-js/extension",
    "jupyter-js-widgets/extension",
    "jupyter_dash/main",
]


def readyz():
    return {"status": "ok"}, 200


def wait_ready(url, timeout=10) -> None:
    """Wait for a solara server at root url to be ready, or throw a TimeoutError

    This uses the /readyz endpoint to check if the server is ready.

    >>> solara.server.server.wait_ready("http://localhost:8888")
    ...

    """
    t0 = time.time()
    while True:
        try:
            r = requests.get(url + "/readyz")
            if r.status_code == 200:
                return
        except Exception:
            pass
        time.sleep(0.1)
        if time.time() - t0 > timeout:
            raise TimeoutError(f"Timeout waiting for {url}")


def is_ready(url) -> bool:
    """Returns whether a solara server at root url is ready.

    This uses the /readyz endpoint to check if the server is ready.

    >>> solara.server.server.is_ready("http://localhost:8888")
    True

    """
    try:
        r = requests.get(url + "/readyz")
        if r.status_code == 200:
            return True
    except Exception:
        pass
    return False


async def app_loop(ws: websocket.WebsocketWrapper, session_id: str, connection_id: str, user: dict = None):
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
    with run_context, context:
        if user:
            from solara_enterprise.auth import user as solara_user

            solara_user.set(user)

        while True:
            try:
                message = await ws.receive()
            except websocket.WebSocketDisconnect:
                logger.debug("Disconnected")
                return
            t0 = time.time()
            if isinstance(message, str):
                msg = json.loads(message)
            else:
                msg = deserialize_binary_message(message)
            t1 = time.time()
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

    if ipykernel_major < 6:
        # the channel argument was added in 6.0
        kernel.set_parent(None, msg)
    else:
        kernel.set_parent(None, msg, msg["channel"])
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
            msg = session.send(
                kernel.shell_stream,
                "comm_info_reply",
                reply_content,
                msg["header"],
                None,
            )
    else:
        logger.error("Unsupported msg with msg_type %r", msg_type)


def read_root(path: str, root_path: str = "", render_kwargs={}, use_nbextensions=True) -> Optional[str]:
    default_app = app.apps["__default__"]
    routes = default_app.routes
    router = solara.routing.Router(path, routes)
    if not router.possible_match:
        return None
    if use_nbextensions:
        nbextensions = get_nbextensions()
    else:
        nbextensions = []

    resources = {
        "theme": "light",
        "nbextensions": nbextensions,
    }
    template: jinja2.Template = get_jinja_env(app_name="__default__").get_template(template_name)
    pre_rendered_html = ""
    pre_rendered_css = ""
    pre_rendered_metas = ""
    title = "Solara ☀️"
    if settings.ssg.enabled:
        from solara_enterprise import ssg

        ssg_data = ssg.ssg_data(path)
        if ssg_data is not None:
            pre_rendered_html = ssg_data["html"]
            pre_rendered_css = "\n".join(ssg_data["styles"])
            pre_rendered_metas = "\n    ".join(ssg_data["metas"])
            title = ssg_data["title"]

    if settings.assets.proxy:
        # solara acts as a proxy
        cdn = f"{root_path}/_solara/cdn"
    else:
        cdn = settings.assets.cdn

    render_settings = {
        "title": title,
        "path": path,
        "root_path": root_path,
        "resources": resources,
        "theme": settings.theme.dict(),
        "production": settings.main.mode == "production",
        "pre_rendered_html": pre_rendered_html,
        "pre_rendered_css": pre_rendered_css,
        "pre_rendered_metas": pre_rendered_metas,
        "assets": settings.assets.dict(),
        "cdn": cdn,
        "ipywidget_major_version": ipywidgets_major,
        "platform": settings.main.platform,
        **render_kwargs,
    }
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


@solara.memoize(storage=cache_memory)
def get_nbextensions_directories() -> List[Path]:
    from jupyter_core.paths import jupyter_path

    all_nb_directories = [Path(k) for k in jupyter_path("nbextensions")]
    # FIXME: remove IPython nbextensions path after a migration period
    try:
        from IPython.paths import get_ipython_dir
    except ImportError:
        pass
    else:
        all_nb_directories.append(Path(get_ipython_dir()) / "nbextensions")
    return [Path(k) for k in all_nb_directories]


@solara.memoize(storage=cache_memory)
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


nbextensions_directories = get_nbextensions_directories()
solara_static = Path(__file__).parent / "static"
