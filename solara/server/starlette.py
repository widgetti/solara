import logging
import os
import pathlib
import typing
from typing import List, Union, cast
from uuid import uuid4

import anyio
import starlette.websockets
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Mount, Route, WebSocketRoute
from starlette.staticfiles import StaticFiles

import solara
from solara.server import reload

from . import app as appmod
from . import patch, server, settings, websocket
from .cdn_helper import cdn_url_path, default_cache_dir, get_path

os.environ["SERVER_SOFTWARE"] = "solara/" + str(solara.__version__)

logger = logging.getLogger("solara.server.fastapi")
# if we add these to the router, the server_test does not run (404's)
prefix = ""


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


async def kernels(id):
    return JSONResponse({"name": "lala", "id": "dsa"})


async def kernel_connection(ws: starlette.websockets.WebSocket):
    session_id = ws.cookies.get(server.COOKIE_KEY_SESSION_ID)
    if not session_id:
        logger.error("no session cookie")
        await ws.close()
        return
    connection_id = ws.query_params["session_id"]
    if not connection_id:
        logger.error("no session_id/connection_id")
        await ws.close()
        return
    logger.info("Solara kernel requested for session_id=%s connection_id=%s", session_id, connection_id)
    await ws.accept()

    def websocket_thread_runner(ws: starlette.websockets.WebSocket, portal: anyio.from_thread.BlockingPortal):
        ws_wrapper = WebsocketWrapper(ws, portal)

        async def run():
            try:
                assert session_id is not None
                assert connection_id is not None
                await server.app_loop(ws_wrapper, session_id, connection_id)
            except:  # noqa
                await portal.stop(cancel_remaining=True)
                raise

        # sometimes throws: RuntimeError: Already running asyncio in this thread
        anyio.run(run)

    # this portal allows us to sync call the websocket calls from this current event loop we are in
    # each websocket however, is handled from a separate thread
    try:
        async with anyio.from_thread.BlockingPortal() as portal:
            thread_return = anyio.to_thread.run_sync(websocket_thread_runner, ws, portal)
            await thread_return
    finally:
        try:
            await ws.close()
        except:  # noqa
            pass


async def close(request: Request):
    connection_id = request.path_params["connection_id"]
    if connection_id in appmod.contexts:
        context = appmod.contexts[connection_id]
        context.close()
    response = HTMLResponse(content="", status_code=200)
    return response


async def root(request: Request, fullpath: str = ""):
    root_path = request.scope.get("root_path", "")
    logger.debug("root_path: %s", root_path)
    if request.headers.get("script-name"):
        logger.debug("override root_path using script-name header from %s to %s", root_path, request.headers.get("script-name"))
        root_path = request.headers.get("script-name")
    if request.headers.get("x-script-name"):
        logger.debug("override root_path using x-script-name header from %s to %s", root_path, request.headers.get("x-script-name"))
        root_path = request.headers.get("x-script-name")

    content = server.read_root(root_path)
    response = HTMLResponse(content=content)
    session_id = request.cookies.get(server.COOKIE_KEY_SESSION_ID) or str(uuid4())
    response.set_cookie(server.COOKIE_KEY_SESSION_ID, value=session_id, expires="Fri, 01 Jan 2038 00:00:00 GMT")  # type: ignore
    return response


class StaticNbFiles(StaticFiles):
    def get_directories(
        self,
        directory: Union[str, "os.PathLike[str]", None] = None,
        packages=None,  # type: ignore
    ) -> List[Union[str, "os.PathLike[str]"]]:
        return cast(List[Union[str, "os.PathLike[str]"]], server.nbextensions_directories)

    # allow us to follow symlinks, maybe only in dev mode?
    # from https://github.com/encode/starlette/pull/1377/files
    def lookup_path(self, path: str) -> typing.Tuple[str, typing.Optional[os.stat_result]]:
        if settings.main.mode == "production":
            return super().lookup_path(path)
        if settings.main.mode == "development":
            for directory in self.all_directories:
                original_path = os.path.join(directory, path)
                full_path = os.path.realpath(original_path)
                directory = os.path.realpath(directory)
                try:
                    return full_path, os.stat(full_path)
                except (FileNotFoundError, NotADirectoryError):
                    continue
            return "", None
        raise ValueError(f"Unknown mode {settings.main.mode}")


class StaticPublic(StaticFiles):
    def get_directories(
        self,
        directory: Union[str, "os.PathLike[str]", None] = None,
        packages=None,  # type: ignore
    ) -> List[Union[str, "os.PathLike[str]"]]:
        # we only know the .directory at runtime (after startup)
        # which means we cannot pass the directory to the StaticFiles constructor
        return cast(List[Union[str, "os.PathLike[str]"]], [app.directory.parent / "public" for app in appmod.apps.values()])


class StaticAssets(StaticFiles):
    def get_directories(
        self,
        directory: Union[str, "os.PathLike[str]", None] = None,
        packages=None,  # type: ignore
    ) -> List[Union[str, "os.PathLike[str]"]]:
        # we only know the .directory at runtime (after startup)
        # which means we cannot pass the directory to the StaticFiles constructor
        overrides = [app.directory.parent / "assets" for app in appmod.apps.values()]
        default = server.solara_static.parent / "assets"
        return cast(List[Union[str, "os.PathLike[str]"]], [*overrides, default])


class StaticCdn(StaticFiles):
    def lookup_path(self, path: str) -> typing.Tuple[str, typing.Optional[os.stat_result]]:
        full_path = get_path(pathlib.Path(default_cache_dir), path)
        return full_path, os.stat(full_path)


def on_startup():
    reload.reloader.start()


routes = [
    Route("/jupyter/api/kernels/{id}", endpoint=kernels),
    WebSocketRoute("/jupyter/api/kernels/{id}/{name}", endpoint=kernel_connection),
    Route("/", endpoint=root),
    Route("/{fullpath}", endpoint=root),
    Route("/_solara/api/close/{connection_id}", endpoint=close, methods=["POST"]),
    Mount(f"/{cdn_url_path}", app=StaticCdn(directory=default_cache_dir)),
    Mount(f"{prefix}/static/public", app=StaticPublic()),
    Mount(f"{prefix}/static/assets", app=StaticAssets()),
    Mount(f"{prefix}/static/nbextensions", app=StaticNbFiles()),
    Mount(f"{prefix}/static/nbconvert", app=StaticFiles(directory=server.nbconvert_static)),
    Mount(f"{prefix}/static", app=StaticFiles(directory=server.solara_static)),
    Route("/{fullpath:path}", endpoint=root),
]
app = Starlette(
    routes=routes,
    on_startup=[on_startup],
)
patch.patch()
