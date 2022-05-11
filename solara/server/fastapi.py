import asyncio
import logging
import os
import typing
from pathlib import Path
from typing import List, Optional, Union, cast

import anyio
import starlette.websockets
from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import HTMLResponse
from starlette.staticfiles import StaticFiles

from . import app as appmod
from . import patch, server, websocket

logger = logging.getLogger("solara.server.fastapi")
# if we add these to the router, the server_test does not run (404's)
prefix = ""
router = APIRouter()
directory = Path(__file__).parent


class WebsocketWrapper(websocket.WebsocketWrapper):
    ws: starlette.websockets.WebSocket

    def __init__(self, ws: starlette.websockets.WebSocket, portal: anyio.from_thread.BlockingPortal) -> None:
        self.ws = ws
        self.portal = portal

    def close(self):
        self.portal.call(self.close)

    def send_text(self, data: str) -> None:
        self.portal.call(self.ws.send_text, data)

    def send_bytes(self, data: bytes) -> None:
        self.portal.call(self.ws.send_bytes, data)

    def receive(self):
        message = self.portal.call(self.ws.receive)
        if "text" in message:
            return message["text"]
        elif "bytes" in message:
            return message["bytes"]
        elif message.get("type") == "websocket.disconnect":
            raise websocket.WebSocketDisconnect()
        else:
            raise RuntimeError(f"Unknown message type {message}")


@router.get("/jupyter/api/kernels/{id}")
async def kernels(id):
    return {"name": "lala", "id": "dsa"}


@router.websocket("/jupyter/api/kernels/{id}/{name}")
async def kernels_connection(ws: starlette.websockets.WebSocket, id, name, session_id: Optional[str] = None):
    context_id = ws.cookies.get(appmod.COOKIE_KEY_CONTEXT_ID)
    logger.info("Solara kernel requested for context_id %s (%s, %s, %s)", context_id, id, name, session_id)
    await ws.accept()

    def websocket_thread_runner(ws: starlette.websockets.WebSocket, context_id: str, portal: anyio.from_thread.BlockingPortal):
        ws_wrapper = WebsocketWrapper(ws, portal)
        anyio.run(server.app_loop, ws_wrapper, context_id)

    # this portal allows us to sync call the websocket calls from this current event loop we are in
    # each websocket however, is handled from a separate thread
    async with anyio.from_thread.BlockingPortal() as portal:
        thread_return = anyio.to_thread.run_sync(websocket_thread_runner, ws, context_id, portal)
        await asyncio.gather(portal.sleep_until_stopped(), thread_return)


@router.websocket("/solara/watchdog/")
async def watchdog(ws: starlette.websockets.WebSocket):
    await ws.accept()
    context_id = ws.cookies.get(appmod.COOKIE_KEY_CONTEXT_ID)

    def websocket_thread_runner(ws: starlette.websockets.WebSocket, context_id: str, portal: anyio.from_thread.BlockingPortal):
        ws_wrapper = WebsocketWrapper(ws, portal)
        # anyio.run(server.app_loop, ws_wrapper, context_id)
        server.control_loop(ws_wrapper, context_id)

    # this portal allows us to sync call the websocket calls from this current event loop we are in
    # each websocket however, is handled from a separate thread
    async with anyio.from_thread.BlockingPortal() as portal:
        thread_return = anyio.to_thread.run_sync(websocket_thread_runner, ws, context_id, portal)
        await asyncio.gather(portal.sleep_until_stopped(), thread_return)


@router.get("/")
@router.get("/{fullpath}")
async def read_root(request: Request, fullpath: Optional[str] = ""):
    root_path = request.scope.get("root_path", "")
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
        return cast(List[Union[str, "os.PathLike[str]"]], server.nbextensions_directories)


app = FastAPI()
app.mount(f"{prefix}/static/dist", StaticFiles(directory=server.voila_static))
app.mount(f"{prefix}/static", StaticFiles(directory=directory / "static"))
app.mount(f"{prefix}/solara/static", StaticFiles(directory=server.nbconvert_static))
app.mount(f"{prefix}/voila/nbextensions", StaticNbFiles())

app.include_router(router=router, prefix=prefix)

patch.patch()
