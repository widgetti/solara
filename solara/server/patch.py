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

from . import app, settings

logger = logging.getLogger("solara.server.app")


class FakeIPython:
    def __init__(self, context: app.AppContext):
        self.context = context

    def showtraceback(self):

        if settings.main.use_pdb:
            logger.exception("Exception, will be handled by debugger")
            pdb.post_mortem()
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
        app.get_current_context()
    except RuntimeError:
        return False
    return True


def display_solara(*objs, include=None, exclude=None, metadata=None, transient=None, display_id=None, raw=False, clear=False, **kwargs):
    print(*objs)


# from IPython.core.interactiveshell import InteractiveShell

# if transient is None:
#     transient = {}
# if metadata is None:
#     metadata = {}
# from IPython.core.display_functions import _new_id

# if display_id:
#     if display_id is True:
#         display_id = _new_id()
#     transient["display_id"] = display_id
# if kwargs.get("update") and "display_id" not in transient:
#     raise TypeError("display_id required for update_display")
# if transient:
#     kwargs["transient"] = transient

# if not objs and display_id:
#     # if given no objects, but still a request for a display_id,
#     # we assume the user wants to insert an empty output that
#     # can be updated later
#     objs = [{}]
#     raw = True

# if not raw:
#     format = InteractiveShell.instance().display_formatter.format

# if clear:
#     clear_output(wait=True)

# for obj in objs:
#     if raw:
#         publish_display_data(data=obj, metadata=metadata, **kwargs)
#     else:
#         format_dict, md_dict = format(obj, include=include, exclude=exclude)
#         if not format_dict:
#             # nothing to display (e.g. _ipython_display_ took over)
#             continue
#         if metadata:
#             # kwarg-specified metadata gets precedence
#             _merge(md_dict, metadata)
#         publish_display_data(data=format_dict, metadata=md_dict, **kwargs)
# if display_id:
#     return DisplayHandle(display_id)


def get_ipython():
    context = app.get_current_context()
    our_fake_ipython = FakeIPython(context)
    return our_fake_ipython


class context_dict(MutableMapping):
    def _get_context_dict(self) -> dict:
        raise NotImplementedError

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


class context_dict_widgets(context_dict):
    def _get_context_dict(self) -> dict:
        context = app.get_current_context()
        return context.widgets


class context_dict_templates(context_dict):
    def _get_context_dict(self) -> dict:
        context = app.get_current_context()
        return context.templates


Thread__init__ = threading.Thread.__init__
Thread__run = threading.Thread.run


def WidgetContextAwareThread__init__(self, *args, **kwargs):
    Thread__init__(self, *args, **kwargs)
    self.current_context = None
    try:
        self.current_context = app.get_current_context()
    except RuntimeError:
        logger.info(f"No context for thread {self}")
    if self.current_context:
        app.set_context_for_thread(self.current_context, self)


def Thread_debug_run(self):
    try:
        Thread__run(self)
    except Exception:
        if settings.main.use_pdb:
            logger.exception("Exception, will be handled by debugger")
            pdb.post_mortem()
        raise


def patch():
    IPython.display.display = display_solara
    __builtins__["display"] = display_solara

    # the ipyvue.Template module cannot be accessed like ipyvue.Template
    # because the import in ipvue overrides it
    template_mod = sys.modules["ipyvue.Template"]
    template_mod.template_registry = context_dict_templates()  # type: ignore
    ipywidgets.widget.Widget.widgets = context_dict_widgets()  # type: ignore
    threading.Thread.__init__ = WidgetContextAwareThread__init__  # type: ignore
    threading.Thread.run = Thread_debug_run  # type: ignore
    ipykernel.kernelbase.Kernel.instance = classmethod(kernel_instance_dispatch)
    ipykernel.kernelbase.Kernel.initialized = classmethod(kernel_initialized_dispatch)
    ipywidgets.widgets.widget.get_ipython = get_ipython
