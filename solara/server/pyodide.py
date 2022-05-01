import json

import ipywidgets
import js

from . import app, patch, server
from .kernel import BytesWrap, Kernel, WebsocketStreamWrapper

context_id = "single"


class Websocket:
    def send(self, msg):
        js.sendToPage(msg)


ws = Websocket()


def start():
    patch.patch()
    kernel = Kernel()
    kernel.shell_stream = WebsocketStreamWrapper(ws, "shell")
    kernel.control_stream = WebsocketStreamWrapper(ws, "control")
    kernel.session.websockets.add(ws)
    context = app.contexts[context_id] = app.AppContext(id=context_id, kernel=kernel, control_sockets=[], widgets={}, templates={})
    app_state = None
    with context:
        ipywidgets.register_comm_target(kernel)
        widget, render_context = server.run_app(app_state)
        context.widgets["content"] = widget
    context.app_object = render_context
    model_id = context.widgets["content"].model_id
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
