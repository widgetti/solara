import logging
import pdb
import sys
import threading
import traceback
from typing import MutableMapping
from unittest import mock

import ipykernel.kernelbase
import IPython.display
import ipywidgets

from . import app, reload, settings

logger = logging.getLogger("solara.server.app")


class FakeIPython:
    def __init__(self, context: app.AppContext):
        self.context = context
        self.kernel = context.kernel
        self.display_pub = mock.MagicMock()
        # needed for the pyplot interface of matplotlib
        # (although we don't really support it)
        self.events = mock.MagicMock()

    def enable_gui(self, gui):
        logger.error("ignoring call to enable_gui(%s)", gui)

    def register_post_execute(self, callback):
        # mpl requires this
        pass

    def set_parent(self, *args):
        pass

    def showtraceback(self):
        if settings.main.use_pdb:
            logger.exception("Exception, will be handled by debugger")
            pdb.post_mortem()
        etype, value, tb = sys.exc_info()
        traceback_string = "".join(traceback.format_exception(etype, value, tb))
        logger.error("Uncaught exception: %s", traceback_string)
        msg = {
            "type": "exception",
            "traceback": traceback_string,
        }

        for socket in self.context.control_sockets:
            try:
                socket.send_json(msg)
            except:  # noqa
                # TODO: should we remove it from the list?
                pass


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
    print(*objs)  # noqa


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


class context_dict_user(context_dict):
    def __init__(self, name):
        self.name = name

    def _get_context_dict(self) -> dict:
        context = app.get_current_context()
        if self.name not in context.user_dicts:
            context.user_dicts[self.name] = {}
        return context.user_dicts[self.name]


def auto_watch_get_template(get_template):
    """Wraps get_template and adds a file listener for automatic .vue file reloading"""

    def wrapper(abs_path):
        template = get_template(abs_path)
        reload.reloader.watcher.add_file(abs_path)
        return template

    return wrapper


Thread__init__ = threading.Thread.__init__
Thread__run = threading.Thread.run


def WidgetContextAwareThread__init__(self, *args, **kwargs):
    Thread__init__(self, *args, **kwargs)
    self.current_context = None
    try:
        self.current_context = app.get_current_context()
    except RuntimeError:
        logger.debug(f"No context for thread {self}")


def Thread_debug_run(self):
    if self.current_context:
        app.set_context_for_thread(self.current_context, self)
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
    template_mod.get_template = auto_watch_get_template(template_mod.get_template)  # type: ignore

    # this module also imports get_template
    template_mod_vue = sys.modules["ipyvue.VueTemplateWidget"]
    template_mod_vue.get_template = template_mod.get_template  # type: ignore

    component_mod_vue = sys.modules["ipyvue.VueComponentRegistry"]
    component_mod_vue.vue_component_registry = context_dict_user("vue_component_registry")  # type: ignore
    component_mod_vue.vue_component_files = context_dict_user("vue_component_files")  # type: ignore

    ipywidgets.widget.Widget.widgets = context_dict_widgets()  # type: ignore
    threading.Thread.__init__ = WidgetContextAwareThread__init__  # type: ignore
    threading.Thread.run = Thread_debug_run  # type: ignore
    # on CI we get a mypy error:
    # solara/server/patch.py:210: error: Cannot assign to a method
    #  solara/server/patch.py:210: error: Incompatible types in assignment (expression has type "classmethod[Any]",\
    #                                     variable has type "Callable[[VarArg(Any), KwArg(Any)], Any]")
    # not sure why we cannot reproduce that locally
    ipykernel.kernelbase.Kernel.instance = classmethod(kernel_instance_dispatch)  # type: ignore
    # on CI we get a mypy error:
    # solara/server/patch.py:211: error: Cannot assign to a method
    # solara/server/patch.py:211: error: Incompatible types in assignment (expression has type "classmethod[Any]", variable has type "Callable[[], Any]")
    # not sure why we cannot reproduce that locally
    ipykernel.kernelbase.Kernel.initialized = classmethod(kernel_initialized_dispatch)  # type: ignore
    ipywidgets.widgets.widget.get_ipython = get_ipython
    IPython.get_ipython = get_ipython
