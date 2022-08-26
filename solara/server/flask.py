import asyncio
import logging
import mimetypes
import os
from pathlib import Path

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
async def kernels(id):
    return {"name": "lala", "id": "dsa"}


@websocket_extension.route("/jupyter/api/kernels/<id>/<name>")
def kernels_connection(ws: simple_websocket.Server, id: str, name: str):
    context_id = request.cookies.get(appmod.COOKIE_KEY_CONTEXT_ID)
    ws_wrapper = WebsocketWrapper(ws)
    asyncio.run(server.app_loop(ws_wrapper, context_id=context_id))


@websocket_extension.route("/solara/watchdog/", websocket=True)
def watchdog(ws: simple_websocket.Server):
    ws_wrapper = WebsocketWrapper(ws)
    context_id = request.cookies.get(appmod.COOKIE_KEY_CONTEXT_ID)
    server.control_loop(ws_wrapper, context_id)


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
async def read_root(path):
    base_url = url_for(".read_root")
    if base_url.endswith("/"):
        base_url = base_url[:-1]
    context_id = request.cookies.get(appmod.COOKIE_KEY_CONTEXT_ID)
    content, context_id = server.read_root(context_id, path, base_url=base_url)
    assert context_id is not None
    response = flask.Response(content, mimetype="text/html")
    response.set_cookie(appmod.COOKIE_KEY_CONTEXT_ID, value=context_id)
    return response


# using the blueprint and websocket blueprint makes it easier to integrate into other applications
websocket_extension.init_app(blueprint)
app = Flask(__name__)
app.register_blueprint(blueprint)


if __name__ == "__main__":
    from .patch import patch

    patch()
    app.run(debug=False, port=8765)
