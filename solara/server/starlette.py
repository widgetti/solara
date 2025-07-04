import asyncio
import json
import logging
import math
import os
from pathlib import Path
import sys
import threading
import typing
from typing import Any, Dict, List, Optional, Set, Union, cast
from uuid import uuid4
import warnings

import anyio
import starlette.websockets
import uvicorn.server
import websockets.legacy.http
import websockets.exceptions

from solara.server.utils import path_is_child_of

try:
    import solara_enterprise

    del solara_enterprise
    has_solara_enterprise = True
except ImportError:
    has_solara_enterprise = False
if has_solara_enterprise and sys.version_info[:2] > (3, 6):
    has_auth_support = True
    from solara_enterprise.auth.middleware import MutateDetectSessionMiddleware
    from solara_enterprise.auth.starlette import (
        AuthBackend,
        authorize,
        get_user,
        login,
        logout,
    )
else:
    has_auth_support = False

from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.middleware import Middleware
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.requests import HTTPConnection, Request
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from starlette.routing import Mount, Route, WebSocketRoute
from starlette.staticfiles import StaticFiles
from starlette.types import Receive, Scope, Send

import solara
import solara.settings
from solara.server.threaded import ServerBase

from . import app as appmod
from . import kernel_context, server, settings, telemetry, websocket
from .cdn_helper import cdn_url_path, get_path

os.environ["SERVER_SOFTWARE"] = "solara/" + str(solara.__version__)
limiter: Optional[anyio.CapacityLimiter] = None
lock = threading.Lock()


def _ensure_limiter():
    # in older anyios (<4) the limiter can only be created in an async context
    # so we call this in a starlette handler
    global limiter
    if limiter is None:
        with lock:
            if limiter is None:
                limiter = anyio.CapacityLimiter(settings.kernel.max_count if settings.kernel.max_count is not None else math.inf)


logger = logging.getLogger("solara.server.fastapi")
# if we add these to the router, the server_test does not run (404's)
prefix = ""

# The limit for starlette's http traffic should come from h11's DEFAULT_MAX_INCOMPLETE_EVENT_SIZE=16kb
# In practice, testing with 132kb cookies (server_test.py:test_large_cookie) seems to work fine.
# For the websocket, the limit is set to 4kb till 10.4, see
#  * https://github.com/aaugustin/websockets/blob/10.4/src/websockets/legacy/http.py#L14
# Later releases should set this to 8kb. See
#  * https://github.com/aaugustin/websockets/commit/8ce4739b7efed3ac78b287da7fb5e537f78e72aa
#  * https://github.com/aaugustin/websockets/issues/743
# Since starlette seems to accept really large values for http, lets do the same for websockets
# An arbitrarily large value we settled on for now is 32kb
# If we don't do this, users with many cookies will fail to get a websocket connection.
ws_major_version = int(websockets.__version__.split(".")[0])
if ws_major_version >= 13:
    websockets.legacy.http.MAX_LINE_LENGTH = int(os.environ.get("WEBSOCKETS_MAX_LINE_LENGTH", str(1024 * 32)))  # type: ignore
else:
    websockets.legacy.http.MAX_LINE = 1024 * 32  # type: ignore


class WebsocketDebugInfo:
    lock = threading.Lock()
    attempts = 0
    connecting = 0
    open = 0
    closed = 0


class WebsocketWrapper(websocket.WebsocketWrapper):
    ws: starlette.websockets.WebSocket

    def __init__(self, ws: starlette.websockets.WebSocket, portal: Optional[anyio.from_thread.BlockingPortal]) -> None:
        self.ws = ws
        self.portal = portal
        self.to_send: List[Union[str, bytes]] = []
        # following https://docs.python.org/3/library/asyncio-task.html#asyncio.create_task
        # we store a strong reference
        self.tasks: Set[asyncio.Task] = set()
        self.event_loop = asyncio.get_event_loop()
        self._thread_id = threading.get_ident()
        if settings.main.experimental_performance:
            self.task = asyncio.ensure_future(self.process_messages_task())

    async def process_messages_task(self):
        while True:
            await asyncio.sleep(0.05)
            while len(self.to_send) > 0:
                first = self.to_send.pop(0)
                if isinstance(first, bytes):
                    await self._send_bytes_exc(first)
                else:
                    await self._send_text_exc(first)

    async def _send_bytes_exc(self, data: bytes):
        # make sures we catch the starlette/websockets specific exception
        # and re-raise it as a websocket.WebSocketDisconnect
        try:
            await self.ws.send_bytes(data)
        except RuntimeError as e:
            # starlette throws a RuntimeError once you call send after the connection is closed
            # or RuntimeError: Unexpected ASGI message 'websocket.send', after sending 'websocket.close' or response already completed.
            # from uvicorn.protocols.websockets.websockets_impl.py
            if "close message" in repr(e) or "websocket.close" in repr(e):
                raise websocket.WebSocketDisconnect() from e
            else:
                raise
        except (websockets.exceptions.ConnectionClosed, starlette.websockets.WebSocketDisconnect, RuntimeError) as e:
            raise websocket.WebSocketDisconnect() from e

    async def _send_text_exc(self, data: str):
        # make sures we catch the starlette/websockets specific exception
        # and re-raise it as a websocket.WebSocketDisconnect
        try:
            await self.ws.send_text(data)
        except RuntimeError as e:
            if "close message" in repr(e) or "websocket.close" in repr(e):
                raise websocket.WebSocketDisconnect() from e
            else:
                raise
        except (websockets.exceptions.ConnectionClosed, starlette.websockets.WebSocketDisconnect, RuntimeError) as e:
            raise websocket.WebSocketDisconnect() from e

    def close(self):
        async def _close_exc():
            try:
                await self.ws.close()
            except RuntimeError as e:
                if "close message" in repr(e) or "websocket.close" in repr(e):
                    raise websocket.WebSocketDisconnect() from e
                else:
                    raise
            except (websockets.exceptions.ConnectionClosed, starlette.websockets.WebSocketDisconnect, RuntimeError) as e:
                raise websocket.WebSocketDisconnect() from e

        if self.portal is None:
            asyncio.ensure_future(_close_exc())
        else:
            self.portal.call(_close_exc)

    def send_text(self, data: str) -> None:
        if self.portal is None:
            task = self.event_loop.create_task(self._send_text_exc(data))
            self.tasks.add(task)
            task.add_done_callback(self.tasks.discard)
        else:
            if settings.main.experimental_performance:
                self.to_send.append(data)
            else:
                if self._thread_id == threading.get_ident():
                    warnings.warn("""You are triggering a websocket send from the event loop thread.
Support for this is experimental, and to avoid this message, make sure you trigger updates
that trigger this from a different thread, e.g.:

from anyio import to_thread
await to_thread.run_sync(my_update)
""")
                    task = self.event_loop.create_task(self._send_text_exc(data))
                    self.tasks.add(task)
                    task.add_done_callback(self.tasks.discard)
                else:
                    self.portal.call(self._send_text_exc, data)

    def send_bytes(self, data: bytes) -> None:
        if self.portal is None:
            task = self.event_loop.create_task(self._send_bytes_exc(data))
            self.tasks.add(task)
            task.add_done_callback(self.tasks.discard)
        else:
            if settings.main.experimental_performance:
                self.to_send.append(data)
            else:
                if self._thread_id == threading.get_ident():
                    warnings.warn("""You are triggering a websocket send from the event loop thread.
Support for this is experimental, and to avoid this message, make sure you trigger updates
that trigger this from a different thread, e.g.:

from anyio import to_thread
await to_thread.run_sync(my_update)
""")
                    task = self.event_loop.create_task(self._send_bytes_exc(data))
                    self.tasks.add(task)
                    task.add_done_callback(self.tasks.discard)

                self.portal.call(self._send_bytes_exc, data)

    async def receive(self):
        if self.portal is None:
            message = await asyncio.ensure_future(self.ws.receive())
        else:
            if hasattr(self.portal, "start_task_soon"):
                # version 3+
                fut = self.portal.start_task_soon(self.ws.receive)
            else:
                fut = self.portal.spawn_task(self.ws.receive)

            message = await asyncio.wrap_future(fut)
        if message.get("text") is not None:
            return message["text"]
        elif message.get("bytes") is not None:
            return message["bytes"]
        elif message.get("type") == "websocket.disconnect":
            raise websocket.WebSocketDisconnect()
        else:
            raise RuntimeError(f"Unknown message type {message}")


class ServerStarlette(ServerBase):
    server: uvicorn.server.Server
    name = "starlette"

    def __init__(self, port: int, host: str = "localhost", starlette_app=None, **kwargs):
        super().__init__(port, host, **kwargs)
        self.app = starlette_app or app

    def has_started(self):
        return self.server.started

    def signal_stop(self):
        self.server.should_exit = True
        # this cause uvicorn to not wait for background tasks, e.g.:
        # <Task pending name='Task-55'
        #  coro=<WebSocketProtocol.run_asgi() running at
        #  /.../uvicorn/protocols/websockets/websockets_impl.py:184>
        # wait_for=<Future pending cb=[<TaskWakeupMethWrapper object at 0x16896aa00>()]>
        # cb=[WebSocketProtocol.on_task_complete()]>
        self.server.force_exit = True
        self.server.lifespan.should_exit = True

    def serve(self):
        from uvicorn.config import Config
        from uvicorn.server import Server

        if sys.version_info[:2] < (3, 7):
            # make python 3.6 work
            import asyncio

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # uvloop will trigger a: RuntimeError: There is no current event loop in thread 'fastapi-thread'
        config = Config(self.app, host=self.host, port=self.port, **self.kwargs, access_log=False, loop="asyncio")
        self.server = Server(config=config)
        self.started.set()
        self.server.run()


async def kernels(id):
    return JSONResponse({"name": "lala", "id": "dsa"})


async def kernel_connection(ws: starlette.websockets.WebSocket):
    _ensure_limiter()
    try:
        with WebsocketDebugInfo.lock:
            WebsocketDebugInfo.attempts += 1
            WebsocketDebugInfo.connecting += 1
        await _kernel_connection(ws)
    finally:
        with WebsocketDebugInfo.lock:
            WebsocketDebugInfo.closed += 1
            WebsocketDebugInfo.open -= 1


async def _kernel_connection(ws: starlette.websockets.WebSocket):
    session_id = ws.cookies.get(server.COOKIE_KEY_SESSION_ID)

    if settings.oauth.private and not has_auth_support:
        raise RuntimeError("SOLARA_OAUTH_PRIVATE requires solara-enterprise")
    if has_auth_support and "session" in ws.scope:
        user = get_user(ws)
        if user is None and settings.oauth.private:
            await ws.accept()
            logger.error("app is private, requires login")
            await ws.close(code=1008, reason="app is private, requires login")
            return
    else:
        user = None

    if not session_id:
        logger.warning("no session cookie")
        session_id = "session-id-cookie-unavailable:" + str(uuid4())
    # we use the jupyter session_id query parameter as the key/id
    # for a page scope.
    page_id = ws.query_params["session_id"]
    if not page_id:
        logger.error("no page_id")
    kernel_id = ws.path_params["kernel_id"]
    if not kernel_id:
        logger.error("no kernel_id")
        await ws.close()
        return
    logger.info("Solara kernel requested for session_id=%s kernel_id=%s", session_id, kernel_id)
    await ws.accept()
    with WebsocketDebugInfo.lock:
        WebsocketDebugInfo.connecting -= 1
        WebsocketDebugInfo.open += 1

    async def run(ws_wrapper: WebsocketWrapper):
        if kernel_context.async_context_id is not None:
            kernel_context.async_context_id.set(uuid4().hex)
        assert session_id is not None
        assert kernel_id is not None
        telemetry.connection_open(session_id)
        headers_dict: Dict[str, List[str]] = {}
        for k, v in ws.headers.items():
            if k not in headers_dict.keys():
                headers_dict[k] = [v]
            else:
                headers_dict[k].append(v)
        await server.app_loop(ws_wrapper, ws.cookies, headers_dict, session_id, kernel_id, page_id, user)

    def websocket_thread_runner(ws_wrapper: WebsocketWrapper, portal: anyio.from_thread.BlockingPortal):
        async def run_wrapper():
            try:
                await run(ws_wrapper)
            except:  # noqa
                if portal is not None:
                    await portal.stop(cancel_remaining=True)
                raise
            finally:
                telemetry.connection_close(session_id)

        # sometimes throws: RuntimeError: Already running asyncio in this thread
        anyio.run(run_wrapper)  # type: ignore

    # this portal allows us to sync call the websocket calls from this current event loop we are in
    # each websocket however, is handled from a separate thread
    try:
        if settings.kernel.threaded:
            async with anyio.from_thread.BlockingPortal() as portal:
                ws_wrapper = WebsocketWrapper(ws, portal)
                thread_return = anyio.to_thread.run_sync(websocket_thread_runner, ws_wrapper, portal, limiter=limiter)  # type: ignore
                await thread_return
        else:
            ws_wrapper = WebsocketWrapper(ws, None)
            await run(ws_wrapper)
    finally:
        if settings.main.experimental_performance:
            try:
                ws_wrapper.task.cancel()
            except:  # noqa
                logger.exception("error cancelling websocket task")
        try:
            await ws.close()
        except:  # noqa
            pass


def close(request: Request):
    kernel_id = request.path_params["kernel_id"]
    page_id = request.query_params["session_id"]
    context = kernel_context.contexts.get(kernel_id, None)
    if context is not None:
        context.page_close(page_id)
    response = HTMLResponse(content="", status_code=200)
    return response


async def root(request: Request, fullpath: str = ""):
    forwarded_host = request.headers.get("x-forwarded-host")
    forwarded_proto = request.headers.get("x-forwarded-proto")
    host = request.headers.get("host")
    if forwarded_proto and forwarded_proto != request.scope["scheme"]:
        warnings.warn(f"""Header x-forwarded-proto={forwarded_proto!r} does not match scheme={request.scope["scheme"]!r} as given by the asgi framework (probably uvicorn)

This might be a configuration mismatch behind a reverse proxy and can cause issues with redirect urls, and auth.

Most likely, you need to trust your reverse proxy server, see:
    https://solara.dev/documentation/getting_started/deploying/self-hosted

If you use uvicorn (the default when you use `solara run`), make sure you
configure the following environment variables for uvicorn correctly:
UVICORN_PROXY_HEADERS=1  # only needed for uvicorn < 0.10, since it is the default after 0.10
FORWARDED_ALLOW_IPS="127.0.0.1"  # 127.0.0.1 is the default, replace this by the ip of the proxy server

Make sure you replace the IP with the correct IP of the reverse proxy server (instead of 127.0.0.1).

If you are sure that only the reverse proxy can reach the solara server, you can consider setting:
FORWARDED_ALLOW_IPS="*" # This can be a security risk, only use when you know what you are doing
""")
    if settings.oauth.private and not has_auth_support:
        raise RuntimeError("SOLARA_OAUTH_PRIVATE requires solara-enterprise")
    root_path = settings.main.root_path or ""
    if not settings.main.base_url:
        # Note:
        # starlette does not respect x-forwarded-host, and therefore
        # base_url and expected_origin below could be different
        # x-forwarded-host should only be considered if the same criteria in
        # uvicorn's ProxyHeadersMiddleware accepts x-forwarded-proto
        settings.main.base_url = str(request.base_url)
    # if not explicltly set,
    configured_root_path = settings.main.root_path
    scope = request.scope
    root_path_asgi = scope.get("route_root_path", scope.get("root_path", ""))
    if settings.main.root_path is None:
        # use the default root path from the app, which seems to also include the path
        # if we are mounted under a path
        root_path = root_path_asgi
        logger.debug("root_path: %s", root_path)
        # or use the script-name header, for instance when running under a reverse proxy
        script_name = request.headers.get("script-name")
        if script_name:
            logger.debug("override root_path using script-name header from %s to %s", root_path, script_name)
            root_path = script_name
        script_name = request.headers.get("x-script-name")
        if script_name:
            logger.debug("override root_path using x-script-name header from %s to %s", root_path, script_name)
            root_path = script_name
        settings.main.root_path = root_path

    # lets be flexible about the trailing slash
    # TODO: maybe we should be more strict about the trailing slash
    naked_root_path = settings.main.root_path.rstrip("/")
    naked_base_url = settings.main.base_url.rstrip("/")
    if not naked_base_url.endswith(naked_root_path):
        msg = f"""base url {naked_base_url!r} does not end with root path {naked_root_path!r}

This could be a configuration mismatch behind a reverse proxy and can cause issues with redirect urls, and auth.

See also https://solara.dev/documentation/getting_started/deploying/self-hosted
"""
        if "script-name" in request.headers:
            msg += f"""It looks like the reverse proxy sets the script-name header to {request.headers["script-name"]!r}
"""
        if "x-script-name" in request.headers:
            msg += f"""It looks like the reverse proxy sets the x-script-name header to {request.headers["x-script-name"]!r}
"""
        if configured_root_path:
            msg += f"""It looks like the root path was configured to {configured_root_path!r} in the settings
"""
        if root_path_asgi:
            msg += f"""It looks like the root path set by the asgi framework was configured to {root_path_asgi!r}
"""
        warnings.warn(msg)
    if host and forwarded_host and forwarded_proto:
        port = request.base_url.port
        ports = {"http": 80, "https": 443}
        expected_origin = f"{forwarded_proto}://{forwarded_host}"
        if port and port != ports[forwarded_proto]:
            expected_origin += f":{port}"
        starlette_origin = settings.main.base_url
        # strip off trailing / because we compare to the naked root path
        starlette_origin = starlette_origin.rstrip("/")
        if naked_root_path:
            # take off the root path
            starlette_origin = starlette_origin[: -len(naked_root_path)]
        if starlette_origin != expected_origin:
            warnings.warn(f"""Origin as determined by starlette ({starlette_origin!r}) does not match expected origin ({expected_origin!r}) based on x-forwarded-proto ({forwarded_proto!r}) and x-forwarded-host ({forwarded_host!r}) headers.

This might be a configuration mismatch behind a reverse proxy and can cause issues with redirect urls, and auth.
Most likely your proxy server sets the host header incorrectly (value for this request was {host!r})

See also https://solara.dev/documentation/getting_started/deploying/self-hosted
""")

    request_path = request.url.path
    if request_path.startswith(root_path):
        request_path = request_path[len(root_path) :]
    if request_path in server._redirects.keys():
        return RedirectResponse(server._redirects[request_path])

    content = server.read_root(request_path, root_path)
    if content is None:
        if settings.oauth.private and not request.user.is_authenticated:
            raise HTTPException(status_code=401, detail="Unauthorized")
        raise HTTPException(status_code=404, detail="Page not found by Solara router")

    if settings.oauth.private and not request.user.is_authenticated:
        from solara_enterprise.auth.starlette import login

        return await login(request)

    response = HTMLResponse(content=content)
    session_id = request.cookies.get(server.COOKIE_KEY_SESSION_ID) or str(uuid4())
    samesite = "lax"
    secure = False
    httponly = settings.session.http_only
    # we want samesite, so we can set a cookie when embedded in an iframe, such as on huggingface
    # however, samesite=none requires Secure https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Set-Cookie/SameSite
    # when hosted on the localhost domain we can always set the Secure flag
    # to allow samesite https://developer.mozilla.org/en-US/docs/Web/HTTP/Cookies#restrict_access_to_cookies
    if request.scope["scheme"] == "https" or request.headers.get("x-forwarded-proto", "http") == "https" or request.base_url.hostname == "localhost":
        samesite = "none"
        secure = True
    elif request.base_url.hostname != "localhost":
        warnings.warn(f"""Cookies with samesite=none require https, but according to the asgi framework, the scheme is {request.scope["scheme"]!r}
and the x-forwarded-proto header is {request.headers.get("x-forwarded-proto", "http")!r}. We will fallback to samesite=lax.

If you embed solara in an iframe, make sure you forward the x-forwarded-proto header correctly so that the session cookie can be set.

See https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Set-Cookie/SameSite for more information on samesite cookies.

Also check out the following Solara documentation:
 * https://solara.dev/documentation/getting_started/deploying/self-hosted
 * https://solara.dev/documentation/advanced/howto/embed
""")
    response.set_cookie(
        server.COOKIE_KEY_SESSION_ID,
        value=session_id,
        expires="Fri, 01 Jan 2038 00:00:00 GMT",
        samesite=samesite,  # type: ignore
        secure=secure,  # type: ignore
        httponly=httponly,  # type: ignore
    )  # type: ignore
    return response


class StaticFilesOptionalAuth(StaticFiles):
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        conn = HTTPConnection(scope)
        if settings.oauth.private and not has_auth_support:
            raise RuntimeError("SOLARA_OAUTH_PRIVATE requires solara-enterprise")
        if has_auth_support and settings.oauth.private and not conn.user.is_authenticated:
            raise HTTPException(status_code=401, detail="Unauthorized")
        await super().__call__(scope, receive, send)


class StaticNbFiles(StaticFilesOptionalAuth):
    def get_directories(
        self,
        directory: Union[str, "os.PathLike[str]", None] = None,
        packages=None,  # type: ignore
    ) -> List[Union[str, "os.PathLike[str]"]]:
        return cast(List[Union[str, "os.PathLike[str]"]], server.nbextensions_directories)

    # follow symlinks
    # from https://github.com/encode/starlette/pull/1377/files
    def lookup_path(self, path: str) -> typing.Tuple[str, typing.Optional[os.stat_result]]:
        for directory in self.all_directories:
            directory = os.path.realpath(directory)
            original_path = os.path.join(directory, path)
            full_path = os.path.realpath(original_path)
            # return early if someone tries to access a file outside of the directory
            if not path_is_child_of(Path(original_path), Path(directory)):
                return "", None
            try:
                return full_path, os.stat(full_path)
            except (FileNotFoundError, NotADirectoryError):
                continue
        return "", None


class StaticPublic(StaticFilesOptionalAuth):
    def lookup_path(self, *args, **kwargs):
        self.all_directories = self.get_directories(None, None)
        return super().lookup_path(*args, **kwargs)

    def get_directories(
        self,
        directory: Union[str, "os.PathLike[str]", None] = None,
        packages=None,  # type: ignore
    ) -> List[Union[str, "os.PathLike[str]"]]:
        # we only know the .directory at runtime (after startup)
        # which means we cannot pass the directory to the StaticFiles constructor
        return cast(List[Union[str, "os.PathLike[str]"]], [app.directory.parent / "public" for app in appmod.apps.values()])


class StaticAssets(StaticFilesOptionalAuth):
    def lookup_path(self, *args, **kwargs):
        self.all_directories = self.get_directories(None, None)
        return super().lookup_path(*args, **kwargs)

    def get_directories(
        self,
        directory: Union[str, "os.PathLike[str]", None] = None,
        packages=None,  # type: ignore
    ) -> List[Union[str, "os.PathLike[str]"]]:
        # we only know the .directory at runtime (after startup)
        # which means we cannot pass the directory to the StaticFiles constructor
        directories = server.asset_directories()
        return cast(List[Union[str, "os.PathLike[str]"]], directories)


class StaticCdn(StaticFilesOptionalAuth):
    def lookup_path(self, path: str) -> typing.Tuple[str, typing.Optional[os.stat_result]]:
        try:
            full_path = str(get_path(settings.assets.proxy_cache_dir, path))
        except Exception:
            return "", None
        return full_path, os.stat(full_path)


def on_startup():
    appmod.ensure_apps_initialized()
    # TODO: configure and set max number of threads
    # see https://github.com/encode/starlette/issues/1724
    telemetry.server_start()


def on_shutdown():
    # shutdown all kernels
    for context in list(kernel_context.contexts.values()):
        try:
            context.close()
        except:  # noqa
            logger.exception("error closing kernel on shutdown")
    telemetry.server_stop()


def readyz(request: Request):
    json, status = server.readyz()
    return JSONResponse(json, status_code=status)


def _sanitize_for_json(value):
    """Convert infinite values to None for JSON serialization."""
    if isinstance(value, (int, float)) and math.isinf(value):
        return None
    return value


async def resourcez(request: Request):
    _ensure_limiter()
    assert limiter is not None
    data: Dict[str, Any] = {}
    verbose = request.query_params.get("verbose", None) is not None
    data["websockets"] = {
        "attempts": WebsocketDebugInfo.attempts,
        "connecting": WebsocketDebugInfo.connecting,
        "open": WebsocketDebugInfo.open,
        "closed": WebsocketDebugInfo.closed,
    }
    from . import patch

    data["threads"] = {
        "created": patch.ThreadDebugInfo.created,
        "running": patch.ThreadDebugInfo.running,
        "stopped": patch.ThreadDebugInfo.stopped,
        "active": threading.active_count(),
    }
    contexts = list(kernel_context.contexts.values())
    data["kernels"] = {
        "total": len(contexts),
        "has_connected": len([k for k in contexts if kernel_context.PageStatus.CONNECTED in k.page_status.values()]),
        "has_disconnected": len([k for k in contexts if kernel_context.PageStatus.DISCONNECTED in k.page_status.values()]),
        "has_closed": len([k for k in contexts if kernel_context.PageStatus.CLOSED in k.page_status.values()]),
        "limiter": {
            "total_tokens": _sanitize_for_json(limiter.total_tokens),
            "borrowed_tokens": _sanitize_for_json(limiter.borrowed_tokens),
            "available_tokens": _sanitize_for_json(limiter.available_tokens),
        },
    }
    default_limiter = anyio.to_thread.current_default_thread_limiter()
    data["anyio.to_thread.limiter"] = {
        "total_tokens": _sanitize_for_json(default_limiter.total_tokens),
        "borrowed_tokens": _sanitize_for_json(default_limiter.borrowed_tokens),
        "available_tokens": _sanitize_for_json(default_limiter.available_tokens),
    }
    if verbose:
        try:
            import psutil

            def expand(named_tuple):
                return {key: getattr(named_tuple, key) for key in named_tuple._fields}

            data["cpu"] = {}
            try:
                data["cpu"]["percent"] = psutil.cpu_percent()
            except Exception as e:
                data["cpu"]["percent"] = str(e)
            try:
                data["cpu"]["count"] = psutil.cpu_count()
            except Exception as e:
                data["cpu"]["count"] = str(e)
            try:
                data["cpu"]["times"] = expand(psutil.cpu_times())
                data["cpu"]["times"]["per_cpu"] = [expand(x) for x in psutil.cpu_times(percpu=True)]
            except Exception as e:
                data["cpu"]["times"] = str(e)
            try:
                data["cpu"]["times_percent"] = expand(psutil.cpu_times_percent())
                data["cpu"]["times_percent"]["per_cpu"] = [expand(x) for x in psutil.cpu_times_percent(percpu=True)]
            except Exception as e:
                data["cpu"]["times_percent"] = str(e)
            try:
                memory = psutil.virtual_memory()
            except Exception as e:
                data["memory"] = str(e)
            else:
                data["memory"] = {
                    "bytes": expand(memory),
                    "GB": {key: getattr(memory, key) / 1024**3 for key in memory._fields},
                }

        except ModuleNotFoundError:
            pass

    json_string = json.dumps(data, indent=2)
    return Response(content=json_string, media_type="application/json")


middleware = [
    Middleware(GZipMiddleware, minimum_size=1000),
]

if has_auth_support:
    middleware = [
        *middleware,
        Middleware(
            MutateDetectSessionMiddleware,
            secret_key=settings.session.secret_key,  # type: ignore
            session_cookie="solara-session",  # type: ignore
            https_only=settings.session.https_only,  # type: ignore
            same_site=settings.session.same_site,  # type: ignore
        ),
        Middleware(AuthenticationMiddleware, backend=AuthBackend()),
    ]

routes_auth = []
if has_auth_support:
    routes_auth = [
        Route("/_solara/auth/authorize", endpoint=authorize),  #
        Route("/_solara/auth/logout", endpoint=logout),
        Route("/_solara/auth/login", endpoint=login),
    ]
routes = [
    Route("/readyz", endpoint=readyz),
    Route("/resourcez", endpoint=resourcez),
    *routes_auth,
    Route("/jupyter/api/kernels/{id}", endpoint=kernels),
    WebSocketRoute("/jupyter/api/kernels/{kernel_id}/{name}", endpoint=kernel_connection),
    Route("/", endpoint=root),
    Route("/{fullpath}", endpoint=root),
    Route("/_solara/api/close/{kernel_id}", endpoint=close, methods=["POST"]),
    # only enable when the proxy is turned on, otherwise if the directory does not exists we will get an exception
    *([Mount(f"/{cdn_url_path}", app=StaticCdn(directory=settings.assets.proxy_cache_dir))] if solara.settings.assets.proxy else []),
    Mount(f"{prefix}/static/public", app=StaticPublic()),
    Mount(f"{prefix}/static/assets", app=StaticAssets()),
    Mount(f"{prefix}/jupyter/nbextensions", app=StaticNbFiles()),
    Mount(f"{prefix}/static", app=StaticFilesOptionalAuth(directory=server.solara_static)),
    Route("/{fullpath:path}", endpoint=root),
]

app = Starlette(routes=routes, on_startup=[on_startup], on_shutdown=[on_shutdown], middleware=middleware)

# Uncomment the lines below to test solara mouted under a subpath
# def myroot(request: Request):
#     return JSONResponse({"framework": "solara"})

# routes_test_sub = [Route("/", endpoint=myroot), Mount("/foo/", routes=routes)]
# app = Starlette(routes=routes_test_sub, on_startup=[on_startup], on_shutdown=[on_shutdown], middleware=middleware)
