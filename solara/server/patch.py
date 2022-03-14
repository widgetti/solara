import asyncio
import logging
import pdb
import sys
import threading
import traceback
from typing import MutableMapping

import ipykernel.kernelbase
import IPython.display
import ipywidgets

from . import app

logger = logging.getLogger("solara.server.app")


class FakeIPython:
    def __init__(self, context: app.AppContext):
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


def kernel_instance_dispatch(cls, *args, **kwargs):
    context = app.get_current_context()
    return context.kernel


def kernel_initialized_dispatch(cls):
    try:
        _context = app.get_current_context()
    except RuntimeError:
        return False
    return True


def display_solara(*args):
    print(args)


def get_ipython():
    context = app.get_current_context()
    our_fake_ipython = FakeIPython(context)
    ipywidgets.widgets.widget.get_ipython = lambda: our_fake_ipython


class context_dict(MutableMapping):
    def _get_context_dict(self) -> dict:
        context = app.get_current_context()
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


# better to patch the ctor
class WidgetContextAwareThread(threading.Thread):
    def __init__(self, *args, **kwargs):
        super(WidgetContextAwareThread, self).__init__(*args, **kwargs)
        self.current_context = None
        try:
            self.current_context = app.get_current_context()
        except RuntimeError as e:
            logger.info(f"No context for thread {self}")
        if self.current_context:
            app.set_context_for_thread(self.current_context, self)


def patch():
    IPython.display.display = display_solara
    __builtins__["display"] = display_solara
    ipywidgets.widget.Widget.widgets = context_dict()
    threading.Thread = WidgetContextAwareThread
    ipykernel.kernelbase.Kernel.instance = classmethod(kernel_instance_dispatch)
    ipykernel.kernelbase.Kernel.initialized = classmethod(kernel_initialized_dispatch)
