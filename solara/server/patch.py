import asyncio
import sys
import traceback

import IPython.display
import ipywidgets

from .app import AppContext, get_current_context


class FakeIPython:
    def __init__(self, context: AppContext):
        self.context = context

    def showtraceback(self):
        etype, value, tb = sys.exc_info()
        traceback_string = "".join(traceback.format_exception(etype, value, tb))
        msg = {
            "type": "exception",
            "traceback": traceback_string,
        }

        async def sendit():
            for socket in self.context.control_sockets:
                await socket.send_json(msg)

        asyncio.create_task(sendit())


def display_solara(*args):
    print(args)


def get_ipython():
    context = get_current_context()
    our_fake_ipython = FakeIPython(context)
    ipywidgets.widgets.widget.get_ipython = lambda: our_fake_ipython


def patch():
    IPython.display.display = display_solara
    __builtins__["display"] = display_solara
