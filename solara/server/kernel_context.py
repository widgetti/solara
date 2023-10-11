import dataclasses
import logging
import os
import pickle
import threading
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, cast

import ipywidgets as widgets
import reacton
from ipywidgets import DOMWidget, Widget

from . import kernel, kernel_context, websocket
from .kernel import Kernel, WebsocketStreamWrapper

WebSocket = Any
logger = logging.getLogger("solara.server.app")


class Local(threading.local):
    kernel_context_stack: Optional[List[Optional["kernel_context.VirtualKernelContext"]]] = None


local = Local()


@dataclasses.dataclass
class VirtualKernelContext:
    id: str
    kernel: kernel.Kernel
    control_sockets: List[WebSocket] = dataclasses.field(default_factory=list)
    # this is the 'private' version of the normally global ipywidgets.Widgets.widget dict
    # see patch.py
    widgets: Dict[str, Widget] = dataclasses.field(default_factory=dict)
    # same, for ipyvue templates
    # see patch.py
    templates: Dict[str, Widget] = dataclasses.field(default_factory=dict)
    user_dicts: Dict[str, Dict] = dataclasses.field(default_factory=dict)
    # anything we need to attach to the context
    # e.g. for a react app the render context, so that we can store/restore the state
    app_object: Optional[Any] = None
    reload: Callable = lambda: None
    state: Any = None
    container: Optional[DOMWidget] = None

    def display(self, *args):
        print(args)  # noqa

    def __enter__(self):
        if local.kernel_context_stack is None:
            local.kernel_context_stack = []
        key = get_current_thread_key()
        local.kernel_context_stack.append(current_context.get(key, None))
        current_context[key] = self

    def __exit__(self, *args):
        key = get_current_thread_key()
        assert local.kernel_context_stack is not None
        current_context[key] = local.kernel_context_stack.pop()

    def close(self):
        with self:
            if self.app_object is not None:
                if isinstance(self.app_object, reacton.core._RenderContext):
                    try:
                        self.app_object.close()
                    except Exception as e:
                        logger.exception("Could not close render context: %s", e)
                        # we want to continue, so we at least close all widgets
            widgets.Widget.close_all()
            # what if we reference each other
            # import gc
            # gc.collect()
        if self.id in contexts:
            del contexts[self.id]

    def _state_reset(self):
        state_directory = Path(".") / "states"
        state_directory.mkdir(exist_ok=True)
        path = state_directory / f"{self.id}.pickle"
        path = path.absolute()
        try:
            path.unlink()
        except:  # noqa
            pass
        del contexts[self.id]
        key = get_current_thread_key()
        del current_context[key]

    def state_save(self, state_directory: os.PathLike):
        path = Path(state_directory) / f"{self.id}.pickle"
        render_context = self.app_object
        if render_context is not None:
            render_context = cast(reacton.core._RenderContext, render_context)
            state = render_context.state_get()
            with path.open("wb") as f:
                logger.debug("State: %r", state)
                pickle.dump(state, f)


contexts: Dict[str, VirtualKernelContext] = {}
# maps from thread key to VirtualKernelContext, if VirtualKernelContext is None, it exists, but is not set as current
current_context: Dict[str, Optional[VirtualKernelContext]] = {}


def create_dummy_context():
    from . import kernel

    kernel_context = VirtualKernelContext(
        id="dummy",
        kernel=kernel.Kernel(),
    )
    return kernel_context


def get_current_thread_key() -> str:
    thread = threading.current_thread()
    return get_thread_key(thread)


def get_thread_key(thread: threading.Thread) -> str:
    thread_key = thread._name + str(thread._ident)  # type: ignore
    return thread_key


def set_context_for_thread(context: VirtualKernelContext, thread: threading.Thread):
    key = get_thread_key(thread)
    current_context[key] = context


def has_current_context() -> bool:
    thread_key = get_current_thread_key()
    return (thread_key in current_context) and (current_context[thread_key] is not None)


def get_current_context() -> VirtualKernelContext:
    thread_key = get_current_thread_key()
    if thread_key not in current_context:
        raise RuntimeError(
            f"Tried to get the current context for thread {thread_key}, but no known context found. This might be a bug in Solara. "
            f"(known contexts: {list(current_context.keys())}"
        )
    context = current_context[thread_key]
    if context is None:
        raise RuntimeError(
            f"Tried to get the current context for thread {thread_key!r}, although the context is know, it was not set for this thread. "
            + "This might be a bug in Solara."
        )
    return context


def set_current_context(context: Optional[VirtualKernelContext]):
    thread_key = get_current_thread_key()
    current_context[thread_key] = context


def initialize_virtual_kernel(kernel_id: str, websocket: websocket.WebsocketWrapper):
    import solara.server.app

    kernel = Kernel()
    logger.info("new virtual kernel: %s", kernel_id)
    context = contexts[kernel_id] = VirtualKernelContext(id=kernel_id, kernel=kernel, control_sockets=[], widgets={}, templates={})
    with context:
        widgets.register_comm_target(kernel)
        solara.server.app.register_solara_comm_target(kernel)
        assert kernel is Kernel.instance()
        kernel.shell_stream = WebsocketStreamWrapper(websocket, "shell")
        kernel.control_stream = WebsocketStreamWrapper(websocket, "control")
        kernel.session.websockets.add(websocket)
    return context
