import asyncio
import logging

import flask
import simple_websocket
from flask import Blueprint, Flask, request, send_from_directory, url_for
from flask_sock import Sock

from . import app as appmod
from . import server, websocket

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


@blueprint.route("/voila/nbextensions/<dir>/<filename>")
def nbext(dir, filename):
    for directory in server.nbextensions_directories:
        file = directory / dir / filename
        if file.exists():
            return send_from_directory(directory / dir, filename)
    return flask.Response("not found", status=404)


@blueprint.route("/static/dist/<path:path>")
def serve_voila_static(path):
    return send_from_directory(server.voila_static, path)


@blueprint.route("/solara/static/<path:path>")
def serve_nbconvert_static(path):
    return send_from_directory(server.nbconvert_static, path)


@blueprint.route("/static/<path:path>")
def serve_static(path):
    return send_from_directory(server.solara_static, path)


@blueprint.route("/", defaults={"path": ""})
@blueprint.route("/<path:path>")
async def read_root(path):
    base_url = url_for(".read_root")
    if base_url.endswith("/"):
        base_url = base_url[:-1]
    print(base_url)
    context_id = request.cookies.get(appmod.COOKIE_KEY_CONTEXT_ID)
    content, context_id = await server.read_root(context_id, base_url=base_url)
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
    app.run(debug=False, port=5002)
