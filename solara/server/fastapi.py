import asyncio
import contextlib
import json
import logging
import os
import sys
import traceback
from pathlib import Path
from typing import Optional
from uuid import uuid4

import IPython.display
import ipywidgets as widgets
import react_ipywidgets
import websockets.exceptions
from fastapi import APIRouter, FastAPI, Request, Response, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from jupyter_core.paths import jupyter_config_path, jupyter_path
from jupyter_server.services.config import ConfigManager
from react_ipywidgets.core import Element, render
from starlette.responses import JSONResponse

from ..kitchensink import *
from .app import AppContext, AppScript, contexts
from .kernel import BytesWrap, Kernel, WebsocketStreamWrapper

COOKIE_KEY_CONTEXT_ID = "solara-context-id"
directory = Path(__file__).parent


solara_app = AppScript(os.environ.get("SOLARA_APP", "solara.examples:app"))


# if asyncio.get_event_loop():
#     asyncio.create_task(solara_app.watch_app())


router = APIRouter()
templates = Jinja2Templates(directory=str(directory / "templates"))


# _kernel_spec = {
#     "display_name": "widgett-kernel",
#     "language": "python",
#     "argv": ["python", "doesnotworkthisway"],
#     "env": {},
#     "language": "python",
#     "interrupt_mode": "signal",
#     "metadata": {},
# }


# @router.get("/jupyter/api/kernelspecs")
# def kernelspecs():
#     return {"default": "flask_kernel", "kernelspecs": {"flask_kernel": {"name": "flask_kernel", "resources": {}, "spec": _kernel_spec}}}


# @router.get("/jupyter/api/kernels")
# @router.post("/jupyter/api/kernels")
# def kernels_normal(request: Request):
#     print(request)
#     data = {
#         "id": "4a8a8c6c-188c-40aa-8bab-3c79500a4b26",
#         "name": "flask_kernel",
#         "last_activity": "2018-01-30T19:32:04.563616Z",
#         "execution_state": "starting",
#         "connections": 0,
#     }
#     return JSONResponse(data, status_code=200)


@router.get("/jupyter/api/kernels/{id}")
async def kernels(id):
    return {"name": "lala", "id": "dsa"}


@router.websocket("/jupyter/api/kernels/{id}/{name}")
async def kernels2(ws: WebSocket, id, name, session_id: Optional[str] = None):
    context_id = ws.cookies.get(COOKIE_KEY_CONTEXT_ID)
    print("context_id", context_id, id, name, session_id)
    if context_id is None:
        logging.warning(f"no context id cookie set ({COOKIE_KEY_CONTEXT_ID})")
        await ws.close()
        return
    context = contexts.get(context_id)
    if context is None:
        logging.warning("invalid context id: %r", context_id)
        await ws.close()
        return

    print("kernels api", id, name)
    kernel = context.kernel
    kernel.shell_stream = WebsocketStreamWrapper(ws, "shell")
    kernel.control_stream = WebsocketStreamWrapper(ws, "control")
    # showtraceback
    import ipywidgets.widgets

    await ws.accept()
    # should we use excepthook ?
    kernel.session.websockets.add(ws)
    while True:
        message = await ws.receive()
        if message["type"] == "websocket.disconnect":
            return
        else:
            if "text" in message:
                msg = json.loads(message["text"])
            else:
                from jupyter_server.base.zmqhandlers import deserialize_binary_message

                msg = deserialize_binary_message(message["bytes"])

            msg_serialized = kernel.session.serialize(msg)
            channel = msg["channel"]
            msg_id = msg["header"]["msg_id"]
            if channel == "shell":
                msg = [BytesWrap(k) for k in msg_serialized]
                await kernel.dispatch_shell(msg)
            else:
                print("unknown channel", msg["channel"])


@router.websocket("/solara/watchdog/")
async def watchdog(ws: WebSocket):
    context_id = ws.cookies.get(COOKIE_KEY_CONTEXT_ID)
    print("watchdog", context_id)
    await ws.accept()
    if context_id is None:
        await ws.send_json({"type": "error", "reason": "no context id found in cookie"})
        await ws.close()
        return
    context = contexts.get(context_id)
    if context:
        contexts[context_id].control_sockets.append(ws)
    ok = True
    while ok:
        try:
            if context_id not in contexts:
                await ws.send_json({"type": "reload", "reason": "context id does not exist (server reload?)"})
            else:
                await ws.send_json({"type": "ping", "reason": "check connection"})
            await asyncio.sleep(0.5)
        except websockets.exceptions.ConnectionClosed:
            context = contexts.get(context_id)
            if context:
                print("closed", context_id)
                context.control_sockets.remove(ws)
            ok = False
            await ws.close()


def run_app():
    main_object = solara_app.run()

    if isinstance(main_object, widgets.Widget):
        return main_object
    elif isinstance(main_object, Element):
        # container = widgets.VBox()
        import ipyvuetify

        container = ipyvuetify.Html(tag="div", style_="display: flex; flex: 0 1 auto; align-items: left; justify-content: left")
        # container = ipyvuetify.Html(tag="div")
        render(main_object, container, handle_error=False)
        return container
    else:
        raise ValueError(f"Main object (with name {solara_app.app_name} in {solara_app.path}) is not a Widget or Element, but {type(main_object)}")


@router.get("/")
async def read_root(request: Request):

    context_id = request.cookies.get(COOKIE_KEY_CONTEXT_ID)
    print("root", context_id)
    # context_id = None
    if context_id is None or context_id not in contexts:
        kernel = Kernel.instance()
        widgets.register_comm_target(kernel)
        context_id = str(uuid4())
        context = contexts[context_id] = AppContext(kernel=kernel, control_sockets=[], widgets={})
        try:
            with context:
                widget = run_app()
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
            widget = widgets.HTML(f"<pre>{error}</pre>")
            # raise
        context.widgets["content"] = widget
    else:
        context = contexts[context_id]

    model_id = context.widgets["content"].model_id

    read_config_path = [os.path.join(p, "serverconfig") for p in jupyter_config_path()]
    read_config_path += [os.path.join(p, "nbconfig") for p in jupyter_config_path()]
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
        print(load_extensions.items())
        ignorelist = [
            "jupytext/index",
            'nbextensions_configurator/config_menu/main',
            "jupytext/index",
            "nbdime/index",
            "voila/extension",
            "contrib_nbextensions_help_item/main",
            "execute_time/ExecuteTime",
        ]
        nbextensions = [name for name, enabled in load_extensions.items() if enabled and name not in ignorelist]
    else:
        nbextensions = []

    base_url = "/"
    resources = {
        "theme": "light",
        "nbextensions": nbextensions,
    }
    response = templates.TemplateResponse("vuetify.html", {"request": request, "model_id": model_id, "base_url": base_url, "resources": resources})
    response.set_cookie(COOKIE_KEY_CONTEXT_ID, value=context_id)
    return response


@router.get("/voila/nbextensions/{dir}/{filename}")
def nbext(dir, filename):
    """The path to look for Javascript notebook extensions"""
    paths = jupyter_path("nbextensions")
    # FIXME: remove IPython nbextensions path after a migration period
    try:
        from IPython.paths import get_ipython_dir
    except ImportError:
        pass
    else:
        paths.append(os.path.join(get_ipython_dir(), "nbextensions"))
    for path in paths:
        p = Path(path) / dir / filename
        # print(f"looking for {p} in {path}")
        if p.exists():
            with open(p) as f:
                data = f.read()
            return Response(data)
    return Response("not found", status_code=404)


app = FastAPI()
app.include_router(router=router)

# if we add these to the router, the server_test does not run (404's)
app.mount("/static", StaticFiles(directory=directory / "static"), name="static")
app.mount(
    "/solara/static", StaticFiles(directory=f"{sys.prefix}/share/jupyter/nbconvert/templates/lab/static"), name="static"
)
