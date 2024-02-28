import asyncio
import logging
import mimetypes
import os
import threading
from http.server import HTTPServer
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urlparse
from uuid import uuid4

import flask
import simple_websocket
from flask import Blueprint, Flask, abort, request, send_from_directory, url_for
from flask_sock import Sock

try:
    import solara_enterprise  # type: ignore

    del solara_enterprise

    has_solara_enterprise = True
except ImportError:
    has_solara_enterprise = False

if has_solara_enterprise:
    from solara_enterprise.auth.flask import allowed  # type: ignore
    from solara_enterprise.auth.flask import (
        authorize,
        get_user,
        init_flask,
        login,
        logout,
    )
else:

    def allowed():
        return True


import solara
import solara.settings
from solara.server.threaded import ServerBase

from . import app as appmod
from . import cdn_helper, kernel_context, server, settings, websocket

os.environ["SERVER_SOFTWARE"] = "solara/" + str(solara.__version__)

logger = logging.getLogger("solara.server.flask")
blueprint = Blueprint("blueprint-solara", __name__)
websocket_extension = Sock()


class WebsocketWrapper(websocket.WebsocketWrapper):
    ws: simple_websocket.Server

    def __init__(self, ws: simple_websocket.Server) -> None:
        self.ws = ws
        self.lock = threading.Lock()

    def close(self):
        with self.lock:
            self.ws.close()

    def send_text(self, data: str) -> None:
        with self.lock:
            self.ws.send(data)

    def send_bytes(self, data: bytes) -> None:
        with self.lock:
            self.ws.send(data)

    async def receive(self):
        from anyio import to_thread

        try:
            return await to_thread.run_sync(lambda: self.ws.receive())  # type: ignore
        except simple_websocket.ws.ConnectionClosed:
            raise websocket.WebSocketDisconnect()


class ServerFlask(ServerBase):
    server: Any
    name = "flask"

    def __init__(self, port: int, host: str = "localhost", flask_app=None, url_prefix="", **kwargs):
        super().__init__(port, host, **kwargs)
        self.app = flask_app or app
        self.url_prefix = url_prefix
        self.server = None

    def has_started(self):
        return server.is_ready(f"http://{self.host}:{self.port}{self.url_prefix}")

    def signal_stop(self):
        if self.server:
            assert isinstance(self.server, HTTPServer)
            self.server.shutdown()  # type: ignore

    def serve(self):
        from werkzeug.serving import make_server

        self.server = make_server(self.host, self.port, self.app, threaded=True)  # type: ignore
        assert isinstance(self.server, HTTPServer)
        self.started.set()
        self.server.serve_forever(poll_interval=0.05)  # type: ignore


@blueprint.route("/jupyter/api/kernels/<id>")
def kernels(id):
    if not allowed():
        abort(401)
    return {"name": "lala", "id": "dsa"}


@websocket_extension.route("/jupyter/api/kernels/<kernel_id>/<name>")
def kernels_connection(ws: simple_websocket.Server, kernel_id: str, name: str):
    if not settings.main.base_url:
        settings.main.base_url = url_for("blueprint-solara.read_root", _external=True)
    if settings.oauth.private and not has_solara_enterprise:
        raise RuntimeError("SOLARA_OAUTH_PRIVATE requires solara-enterprise")
    if has_solara_enterprise:
        user = get_user()
        if user is None and settings.oauth.private:
            logger.error("app is private, requires login")
            ws.close(1008, "app is private, requires login")  # policy violation
            return
    else:
        user = None

    try:
        page_id = request.args["session_id"]
        session_id = request.cookies.get(server.COOKIE_KEY_SESSION_ID)
        logger.info("Solara kernel requested for session_id=%s kernel_id=%s", session_id, kernel_id)
        if session_id is None:
            logger.warning("no session cookie")
            session_id = "session-id-cookie-unavailable:" + str(uuid4())
        ws_wrapper = WebsocketWrapper(ws)
        headers_dict: Dict[str, List[str]] = {}
        for k, v in request.headers.__iter__():
            if k not in headers_dict.keys():
                headers_dict[k] = [v]
            else:
                headers_dict[k].append(v)
        asyncio.run(
            server.app_loop(
                ws_wrapper,
                cookies=request.cookies.to_dict(),
                headers=headers_dict,
                session_id=session_id,
                kernel_id=kernel_id,
                page_id=page_id,
                user=user,
            )
        )
    except:  # noqa
        logger.exception("Error in kernel handler")
        raise


@blueprint.route("/_solara/api/close/<kernel_id>", methods=["GET", "POST"])
def close(kernel_id: str):
    page_id = request.args["session_id"]
    if kernel_id in kernel_context.contexts:
        context = kernel_context.contexts[kernel_id]
        context.page_close(page_id)
    return ""


@blueprint.route("/static/public/<path:path>")
def public(path):
    if not allowed():
        abort(401)
    directories = [app.directory.parent / "public" for app in appmod.apps.values()]
    for directory in directories:
        file = directory / path
        if file.exists():
            return send_from_directory(directory, path)
    return flask.Response("not found", status=404)


@blueprint.route("/static/assets/<path:path>")
def assets(path):
    if not allowed():
        abort(401)
    overrides = [app.directory.parent / "assets" for app in appmod.apps.values()]
    default = server.solara_static.parent / "assets"
    directories = [*overrides, default]
    for directory in directories:
        file = directory / path
        if file.exists():
            return send_from_directory(directory, path)
    return flask.Response("not found", status=404)


@blueprint.route("/static/nbextensions/<dir>/<filename>")
def nbext(dir, filename):
    if not allowed():
        abort(401)
    for directory in server.nbextensions_directories:
        file = directory / dir / filename
        if file.exists():
            return send_from_directory(directory / dir, filename)
    return flask.Response("not found", status=404)


@blueprint.route("/static/<path:path>")
def serve_static(path):
    if not allowed():
        abort(401)
    return send_from_directory(server.solara_static, path)


if solara.settings.assets.proxy:

    @blueprint.route(f"/{cdn_helper.cdn_url_path}/<path:path>")
    def cdn(path):
        if not allowed():
            abort(401)
        cache_directory = settings.assets.proxy_cache_dir
        content = cdn_helper.get_data(Path(cache_directory), path)
        mime = mimetypes.guess_type(path)
        return flask.Response(content, mimetype=mime[0])


@blueprint.route("/", defaults={"path": ""})
@blueprint.route("/<path:path>")
def read_root(path):
    root_path = url_for(".read_root")
    if root_path.endswith("/"):
        root_path = root_path[:-1]

    if not settings.main.base_url:
        settings.main.base_url = url_for("blueprint-solara.read_root", _external=True)

    session_id = request.cookies.get(server.COOKIE_KEY_SESSION_ID) or str(uuid4())
    if root_path:
        path = flask.request.path[len(root_path) :]
    content = server.read_root(path, root_path=root_path)
    if content is None:
        if not allowed():
            abort(401)
        return flask.Response("not found", status=404)

    if not allowed():
        return login()

    samesite = "lax"
    secure = False
    # we want samesite, so we can set a cookie when embedded in an iframe, such as on huggingface
    # however, samesite=none requires Secure https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Set-Cookie/SameSite
    # when hosted on the localhost domain we can always set the Secure flag
    # to allow samesite https://developer.mozilla.org/en-US/docs/Web/HTTP/Cookies#restrict_access_to_cookies
    o = urlparse(request.base_url)
    if request.headers.get("x-forwarded-proto", "http") == "https" or o.hostname == "localhost":
        samesite = "none"
        secure = True

    assert session_id is not None
    response = flask.Response(content, mimetype="text/html")
    response.set_cookie(server.COOKIE_KEY_SESSION_ID, value=session_id, secure=secure, samesite=samesite)
    return response


if has_solara_enterprise:
    blueprint.route("/_solara/auth/authorize")(authorize)
    blueprint.route("/_solara/auth/logout")(logout)
    blueprint.route("/_solara/auth/login")(login)


@blueprint.route("/readyz")
def readyz():
    json, status = server.readyz()
    return flask.Response(json, mimetype="application/json", status=status)


# using the blueprint and websocket blueprint makes it easier to integrate into other applications
websocket_extension.init_app(blueprint)
app = Flask(__name__, static_url_path="/_static")  # do not intervere with out static files
app.register_blueprint(blueprint)
if has_solara_enterprise:
    init_flask(app)

if __name__ == "__main__":
    app.run(debug=False, port=8765)
