import asyncio
import json
import logging
import os
import sys
import typing
from pathlib import Path
from typing import List, Optional, Union

import websockets.exceptions
from fastapi import APIRouter, FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from starlette.staticfiles import StaticFiles

from . import app as appmod
from . import patch, server
from .kernel import BytesWrap, WebsocketStreamWrapper

logger = logging.getLogger("solara.server.fastapi")

directory = Path(__file__).parent


# if asyncio.get_event_loop():
#     asyncio.create_task(server.solara_app.watch_app())


router = APIRouter()


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
    context_id = ws.cookies.get(appmod.COOKIE_KEY_CONTEXT_ID)
    print("context_id", context_id, id, name, session_id)
    if context_id is None:
        logging.warning(f"no context id cookie set ({appmod.COOKIE_KEY_CONTEXT_ID})")
        await ws.close()
        return
    context = appmod.contexts.get(context_id)
    if context is None:
        logging.warning("invalid context id: %r", context_id)
        await ws.close()
        return

    print("kernels api", id, name)
    kernel = context.kernel
    kernel.shell_stream = WebsocketStreamWrapper(ws, "shell")
    kernel.control_stream = WebsocketStreamWrapper(ws, "control")

    await ws.accept()
    # should we use excepthook ?
    kernel.session.websockets.add(ws)
    if True:
        while True:
            message = await ws.receive()
            if message["type"] == "websocket.disconnect":
                return
            else:
                if "text" in message:
                    msg = json.loads(message["text"])
                else:
                    from jupyter_server.base.zmqhandlers import (
                        deserialize_binary_message,
                    )

                    msg = deserialize_binary_message(message["bytes"])

                msg_serialized = kernel.session.serialize(msg)
                channel = msg["channel"]
                if channel == "shell":
                    msg = [BytesWrap(k) for k in msg_serialized]
                    # TODO: because we use await, we probably need to use a context
                    # manager that sets the app context in a async context, not just thread context
                    with context:
                        await kernel.dispatch_shell(msg)
                else:
                    print("unknown channel", msg["channel"])


@router.websocket("/solara/watchdog/")
async def watchdog(ws: WebSocket):
    context_id = ws.cookies.get(appmod.COOKIE_KEY_CONTEXT_ID)
    print("watchdog", context_id)
    await ws.accept()
    if context_id is None:
        await ws.send_json({"type": "reload", "reason": "no context id found in cookie"})
        await ws.close()
        return
    context = appmod.contexts.get(context_id)
    if context:
        appmod.contexts[context_id].control_sockets.append(ws)
    ok = True

    async def receive_messages():
        while True:
            try:
                text = await ws.receive_text()
            except (WebSocketDisconnect, OSError, RuntimeError) as e:
                print("Oops", e)
                return
            msg = json.loads(text)
            if msg["type"] == "state_reset":
                logger.info(f"reset state for context {context_id}")
                if context:
                    context.state_reset()
                await ws.send_json({"type": "reload", "reason": "context id does not exist (server reload?)"})
            else:
                logger.error("Unknown msg: {msg}")

    asyncio.create_task(receive_messages())
    while ok:
        try:
            if context_id not in appmod.contexts:
                print("closed", context_id)
                await ws.send_json({"type": "reload", "reason": "context id does not exist (server reload?)"})
            else:
                await ws.send_json({"type": "ping", "reason": "check connection"})
            await asyncio.sleep(0.5)
        except (websockets.exceptions.ConnectionClosed, RuntimeError):
            context = appmod.contexts.get(context_id)
            if context:
                print("closed", context_id)
                try:
                    context.control_sockets.remove(ws)
                except ValueError:
                    pass
            ok = False
            try:
                await ws.close()
            except RuntimeError:
                pass  # double close?


@router.get("/")
@router.get("/{fullpath}")
async def read_root(request: Request, fullpath: Optional[str] = ""):

    root_path = request.scope.get("root_path")
    logger.debug("root_path: %s", root_path)
    if request.headers.get("script-name"):
        logger.debug("override root_path using script-name header from %s to %s", root_path, request.headers.get("script-name"))
        root_path = request.headers.get("script-name")
    if request.headers.get("x-script-name"):
        logger.debug("override root_path using x-script-name header from %s to %s", root_path, request.headers.get("x-script-name"))
        root_path = request.headers.get("x-script-name")

    context_id = request.cookies.get(appmod.COOKIE_KEY_CONTEXT_ID)
    content, context_id = await server.read_root(context_id, root_path)
    assert context_id is not None
    response = HTMLResponse(content=content)
    response.set_cookie(appmod.COOKIE_KEY_CONTEXT_ID, value=context_id)
    return response


class StaticNbFiles(StaticFiles):
    def get_directories(
        self, directory: Union[str, "os.PathLike[str]", None] = None, packages: typing.List[str] = None
    ) -> List[Union[str, "os.PathLike[str]"]]:
        all_nb_directories = []
        from jupyter_core.paths import jupyter_path

        all_nb_directories = jupyter_path("nbextensions")
        # FIXME: remove IPython nbextensions path after a migration period
        try:
            from IPython.paths import get_ipython_dir
        except ImportError:
            pass
        else:
            all_nb_directories.append(os.path.join(get_ipython_dir(), "nbextensions"))
        return [Path(k) for k in all_nb_directories]


# if we add these to the router, the server_test does not run (404's)
home = sys.prefix


prefix = ""


def add_static(url, path):
    prefixes = [sys.prefix, os.path.expanduser("~/.local")]
    for prefix in prefixes:
        directory = f"{prefix}{path}"
        if Path(directory).exists():
            app.mount(url, StaticFiles(directory=directory), name="static")
            break
    else:
        raise RuntimeError(f"{path} not found at prefixes: {prefixes}")


app = FastAPI()
add_static(f"{prefix}/static/dist", "/share/jupyter/voila/templates/base/static")
app.mount(f"{prefix}/static", StaticFiles(directory=directory / "static"))
add_static(f"{prefix}/solara/static", "/share/jupyter/nbconvert/templates/lab/static")
app.mount(f"{prefix}/voila/nbextensions", StaticNbFiles())

app.include_router(router=router, prefix=prefix)

patch.patch()
