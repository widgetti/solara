import asyncio
import sys
import traceback
from typing import MutableMapping

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


class context_dict(MutableMapping):
    def _get_context_dict(self) -> dict:
        context = get_current_context()
        return context.widgets

    def __delitem__(self, key) -> None:
        self._get_context_dict().__delitem__(key)

    def __getitem__(self, key):
        return self._get_context_dict().__getitem__(key)

    def __iter__(self):
        return self._get_context_dict().__iter__()

    def __len__(self):
        return self._get_context_dict().__len__()

    def __setitem__(self, key, value):
        self._get_context_dict().__setitem__(key, value)


def patch():
    IPython.display.display = display_solara
    __builtins__["display"] = display_solara
    ipywidgets.widget.Widget.widgets = context_dict()
