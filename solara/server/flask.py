import asyncio
import logging
import mimetypes
import os
from pathlib import Path
from uuid import uuid4

import flask
import simple_websocket
from flask import Blueprint, Flask, request, send_from_directory, url_for
from flask_sock import Sock

import solara

from . import app as appmod
from . import cdn_helper, server, websocket

os.environ["SERVER_SOFTWARE"] = "solara/" + str(solara.__version__)

logger = logging.getLogger("solara.server.flask")
blueprint = Blueprint("blueprint-solara", __name__)
websocket_extension = Sock()


class WebsocketWrapper(websocket.WebsocketWrapper):
    ws: simple_websocket.Server

    def __init__(self, ws: simple_websocket.Server) -> None:
        self.ws = ws

    def close(self):
        self.ws.close()

    def send_text(self, data: str) -> None:
        self.ws.send(data)

    def send_bytes(self, data: bytes) -> None:
        self.ws.send(data)

    def receive(self):
        return self.ws.receive()


@blueprint.route("/jupyter/api/kernels/<id>")
def kernels(id):
    return {"name": "lala", "id": "dsa"}


@websocket_extension.route("/jupyter/api/kernels/<id>/<name>")
def kernels_connection(ws: simple_websocket.Server, id: str, name: str):
    try:
        connection_id = request.args["session_id"]
        session_id = request.cookies.get(server.COOKIE_KEY_SESSION_ID)
        logger.info("Solara kernel requested for session_id=%s connection_id=%s", session_id, connection_id)
        if session_id is None:
            logger.error("no session cookie")
            ws.close()
            return
        ws_wrapper = WebsocketWrapper(ws)
        asyncio.run(server.app_loop(ws_wrapper, session_id=session_id, connection_id=connection_id))
    except:  # noqa
        logger.exception("Error in kernel handler")
        raise


@blueprint.route("/static/public/<path:path>")
def public(path):
    directories = [app.directory.parent / "public" for app in appmod.apps.values()]
    for directory in directories:
        file = directory / path
        if file.exists():
            return send_from_directory(directory, path)
    return flask.Response("not found", status=404)


@blueprint.route("/static/assets/<path:path>")
def assets(path):
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
    for directory in server.nbextensions_directories:
        file = directory / dir / filename
        if file.exists():
            return send_from_directory(directory / dir, filename)
    return flask.Response("not found", status=404)


@blueprint.route("/static/nbconvert/<path:path>")
def serve_nbconvert_static(path):
    return send_from_directory(server.nbconvert_static, path)


@blueprint.route("/static/<path:path>")
def serve_static(path):
    return send_from_directory(server.solara_static, path)


@blueprint.route(f"/{cdn_helper.cdn_url_path}/<path:path>")
def cdn(path):
    cache_directory = cdn_helper.default_cache_dir
    content = cdn_helper.get_data(Path(cache_directory), path)
    mime = mimetypes.guess_type(path)
    return flask.Response(content, mimetype=mime[0])


@blueprint.route("/", defaults={"path": ""})
@blueprint.route("/<path:path>")
def read_root(path):
    base_url = url_for(".read_root")
    if base_url.endswith("/"):
        base_url = base_url[:-1]
    session_id = request.cookies.get(server.COOKIE_KEY_SESSION_ID) or str(uuid4())
    content = server.read_root(base_url=base_url)
    assert session_id is not None
    response = flask.Response(content, mimetype="text/html")
    response.set_cookie(server.COOKIE_KEY_SESSION_ID, value=session_id)
    return response


# using the blueprint and websocket blueprint makes it easier to integrate into other applications
websocket_extension.init_app(blueprint)
app = Flask(__name__)
app.register_blueprint(blueprint)


if __name__ == "__main__":
    from .patch import patch

    patch()
    app.run(debug=False, port=8765)
