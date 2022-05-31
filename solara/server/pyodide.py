import json
from typing import Union

import ipywidgets
import js

from . import app, patch, server
from .kernel import BytesWrap, Kernel, WebsocketStreamWrapper
from .websocket import WebsocketWrapper

context_id = "single"


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


def start():
    patch.patch()
    kernel = Kernel()
    kernel.shell_stream = WebsocketStreamWrapper(ws, "shell")
    kernel.control_stream = WebsocketStreamWrapper(ws, "control")
    context = app.contexts[context_id] = app.AppContext(id=context_id, kernel=kernel, control_sockets=[], widgets={}, templates={})
    app_state = None
    with context:
        ipywidgets.register_comm_target(kernel)
        widget, render_context = server.run_app(app_state)
        context.widgets["content"] = widget
    context.app_object = render_context
    model_id = context.widgets["content"].model_id
    kernel.session.websockets.add(ws)
    return model_id


async def processKernelMessage(msg):
    msg = json.loads(msg)
    context = app.contexts[context_id]
    kernel = context.kernel
    msg_serialized = kernel.session.serialize(msg)

    channel = msg["channel"]
    if channel == "shell":
        msg = [BytesWrap(k) for k in msg_serialized]
        # TODO: because we use await, we probably need to use a context
        # manager that sets the app context in a async context, not just thread context
        with context:
            await kernel.dispatch_shell(msg)
    return 42
