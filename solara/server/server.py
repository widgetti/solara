import contextlib
import hashlib
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, TypeVar

import ipykernel
import ipyvue
import ipywidgets
import jinja2
import requests

import solara
import solara.routing
import solara.settings
from solara.lab import cookies as solara_cookies
from solara.lab import headers as solara_headers

from . import app, jupytertools, patch, settings, websocket
from .kernel import Kernel, deserialize_binary_message
from .kernel_context import initialize_virtual_kernel

COOKIE_KEY_SESSION_ID = "solara-session-id"

T = TypeVar("T")


directory = Path(__file__).parent
template_name = "index.html.j2"
ipykernel_major = int(ipykernel.__version__.split(".")[0])
ipywidgets_major = int(ipywidgets.__version__.split(".")[0])
cache_memory = solara.cache.Memory(max_items=128)
vue3 = ipyvue.__version__.startswith("3")

# first look at the project directory, then the builtin solara directory


@solara.memoize(storage=cache_memory)
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


async def app_loop(ws: websocket.WebsocketWrapper, cookies: Dict[str, str], headers, session_id: str, kernel_id: str, page_id: str, user: dict = None):
    context = initialize_virtual_kernel(session_id, kernel_id, ws)
    if context is None:
        logging.warning("invalid kernel id: %r", kernel_id)
        # to avoid very fast reconnects (we are in a thread anyway)
        time.sleep(0.5)
        return

    if settings.main.tracer:
        import viztracer

        output_file = f"viztracer-{page_id}.html"
        run_context = viztracer.VizTracer(output_file=output_file, max_stack_depth=10)
        logger.warning(f"Running with tracer: {output_file}")
    else:
        run_context = solara.util.nullcontext()

    kernel = context.kernel
    try:
        context.page_connect(page_id)
        with run_context, context:
            if user:
                from solara_enterprise.auth import user as solara_user

                solara_user.set(user)

            solara_cookies.set(cookies)  # type: ignore
            solara_headers.set(headers)  # type: ignore

            while True:
                if settings.main.timing:
                    widgets_ids = set(patch.widgets)
                try:
                    message = await ws.receive()
                except websocket.WebSocketDisconnect:
                    try:
                        context.kernel.session.websockets.remove(ws)
                    except KeyError:
                        pass
                    logger.debug("Disconnected")
                    break
                t0 = time.time()
                if isinstance(message, str):
                    msg = json.loads(message)
                else:
                    msg = deserialize_binary_message(message)
                t1 = time.time()
                if not process_kernel_messages(kernel, msg):
                    # if we shut down the kernel, we do not keep the page session alive
                    context.close()
                    return
                t2 = time.time()
                if settings.main.timing:
                    widgets_ids_after = set(patch.widgets)
                    created_widgets_count = len(widgets_ids_after - widgets_ids)
                    close_widgets_count = len(widgets_ids - widgets_ids_after)
                    print(  # noqa: T201
                        f"timing: total={t2-t0:.3f}s, deserialize={t1-t0:.3f}s, kernel={t2-t1:.3f}s"
                        f" widget: created: {created_widgets_count} closed: {close_widgets_count}"
                    )
    finally:
        context.page_disconnect(page_id)


def process_kernel_messages(kernel: Kernel, msg: Dict) -> bool:
    session = kernel.session
    assert session is not None
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
        return True
    elif msg_type in ["comm_open", "comm_msg", "comm_close"]:
        with busy_idle(msg["header"]):
            getattr(comm_manager, msg_type)(kernel.shell_stream, None, msg)
        return True
    elif msg_type in ["comm_info_request"]:
        content = msg["content"]
        target_name = msg.get("target_name", None)

        comms = {
            k: dict(target_name=v.target_name) for (k, v) in comm_manager.comms.items() if v.target_name == target_name or target_name is None  # type: ignore
        }
        reply_content = dict(comms=comms, status="ok")
        with busy_idle(msg["header"]):
            msg = session.send(
                kernel.shell_stream,
                "comm_info_reply",
                reply_content,
                msg["header"],
                None,
            )
        return True
    elif msg_type == "shutdown_request":
        send_status("dead", parent=msg["header"])
        return False
    else:
        logger.error("Unsupported msg with msg_type %r", msg_type)
        return False


def read_root(path: str, root_path: str = "", render_kwargs={}, use_nbextensions=True, ssg_data=None) -> Optional[str]:
    if settings.ssg.enabled and ssg_data is None:
        # simply return the pre-rendered html
        from solara_enterprise import ssg

        content = ssg.ssg_content(path)
        if content is not None:
            return content

    default_app = app.apps["__default__"]
    routes = default_app.routes
    router = solara.routing.Router(path, routes)
    if not router.possible_match:
        return None
    if use_nbextensions:
        nbextensions, nbextensions_hashes = get_nbextensions()
    else:
        nbextensions, nbextensions_hashes = [], {}

    from markupsafe import Markup

    def resolve_static_path(path: str) -> Path:
        # this solve a similar problem as the starlette and flask endpoints
        # maybe this can be common code for all of them.
        if path.startswith("/static/public/"):
            directories = [default_app.directory.parent / "public"]
            filename = path[len("/static/public/") :]
        elif path.startswith("/static/assets/"):
            directories = [default_app.directory.parent / "assets", solara_static.parent / "assets"]
            filename = path[len("/static/assets/") :]
        elif path.startswith("/static/"):
            directories = [solara_static.parent / "static"]
            filename = path[len("/static/") :]
        else:
            raise ValueError(f"invalid static path: {path}")
        for directory in directories:
            full_path = directory / filename
            if full_path.exists():
                return full_path
        raise ValueError(f"static path not found: {filename} (path={path}), looked in {directories}")

    def include_css(path: str) -> Markup:
        filepath = resolve_static_path(path)
        content, hash = solara.util.get_file_hash(filepath)
        url = f"{root_path}{path}?v={hash}"
        # when < 10k we embed, also when we use a url, it can be relative, which can break the url
        embed = len(content) < 1024 * 10 and b"url" not in content
        # Always embed the jupyterlab theme CSS to make theme switching possible (see solara.html.j2 template)
        # TODO: Prevent browser from caching the theme CSS files
        if path.endswith("theme-dark.css") or path.endswith("theme-light.css"):
            content_utf8 = content.decode("utf-8")
            code = content_utf8
        elif embed:
            content_utf8 = content.decode("utf-8")
            code = f"<style>/*\npath={path}\n*/\n{content_utf8}</style>"
        else:
            code = f'<link rel="stylesheet" type="text/css" href="{url}">'
        return Markup(code)

    def include_js(path: str, module=False) -> Markup:
        filepath = resolve_static_path(path)
        content, hash = solara.util.get_file_hash(filepath)
        content_utf8 = content.decode("utf-8")
        url = f"{root_path}{path}?v={hash}"
        # when < 10k we embed, but if we use currentScript, it can break things
        embed = len(content) < 1024 * 10 and b"currentScript" not in content
        if embed:
            if module:
                code = f'<script type="module">/*\npath={path}\n*/{content_utf8}</script>'
            else:
                code = f"<script>/*\npath={path}\n*/{content_utf8}</script>"
        else:
            if module:
                code = f'<script type="module" src="{url}"></script>'
            else:
                code = f'<script src="{url}"></script>'
        return Markup(code)

    resources = {
        "theme": "light",
        "nbextensions": nbextensions,
        "nbextensions_hashes": nbextensions_hashes,
        "include_css": include_css,
        "include_js": include_js,
    }
    template: jinja2.Template = get_jinja_env(app_name="__default__").get_template(template_name)
    pre_rendered_html = ""
    pre_rendered_css = ""
    pre_rendered_metas = ""
    title = "Solara ☀️"
    if ssg_data is not None:
        pre_rendered_html = ssg_data["html"]
        pre_rendered_css = "\n".join(ssg_data["styles"])
        pre_rendered_metas = "\n    ".join(ssg_data["metas"])
        title = ssg_data["title"]

    if solara.settings.assets.proxy:
        # solara acts as a proxy
        cdn = f"{root_path}/_solara/cdn"
    else:
        cdn = solara.settings.assets.cdn

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
        "solara_version": solara.__version__,
        "platform": settings.main.platform,
        "vue3": vue3,
        "perform_check": settings.main.mode != "production" and solara.checks.should_perform_solara_check(),
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
def get_nbextensions() -> Tuple[List[str], Dict[str, Optional[str]]]:
    from jupyter_core.paths import jupyter_config_path

    paths = [Path(p) / "nbconfig" for p in jupyter_config_path()]

    load_extensions = jupytertools.get_config(paths, "notebook")["load_extensions"]

    def exists(name):
        for directory in nbextensions_directories:
            if (directory / (name + ".js")).exists():
                return True
        logger.info(f"nbextension {name} not found")
        return False

    def hash_extension(name):
        if sys.version_info[:2] < (3, 9):
            # usedforsecurity is only available in Python 3.9+
            h = hashlib.new("md5")
        else:
            h = hashlib.new("md5", usedforsecurity=False)  # type: ignore

        for directory in nbextensions_directories:
            if (directory / (name + ".js")).exists():
                for file in directory.glob("**/*.*"):
                    data = file.read_bytes()
                    h.update(data)

        return h.hexdigest()

    nbextensions: List[str] = [name for name, enabled in load_extensions.items() if enabled and (name not in nbextensions_ignorelist) and exists(name)]
    nbextensions_hashes = {name: hash_extension(name) for name in nbextensions}
    return nbextensions, nbextensions_hashes


nbextensions_directories = get_nbextensions_directories()
solara_static = Path(__file__).parent / "static"
