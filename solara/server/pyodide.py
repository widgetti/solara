import json
import logging
from typing import Union

import js

from . import app, patch, server
from .websocket import WebsocketWrapper

connection_id = "single"

logger = logging.getLogger("solara.server.pyodide")


class Websocket(WebsocketWrapper):
    def send_text(self, data: str) -> None:
        js.sendToPage(data)

    def send_bytes(self, data: bytes) -> None:
        js.sendToPage(data)

    def close(self) -> None:
        pass

    def receive(self) -> Union[str, bytes]:
        return b""


ws = Websocket()


def start(app_name):
    logger
    app.apps["__default__"].close()
    app.apps["__default__"] = app.AppScript(app_name)
    patch.patch()
    app.initialize_virtual_kernel(connection_id, ws)


async def processKernelMessage(msg):
    msg = json.loads(msg)
    context = app.contexts[connection_id]
    kernel = context.kernel
    with context:
        server.process_kernel_messages(kernel, msg)
    return 42
