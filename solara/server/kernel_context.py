import asyncio
import sys

try:
    import contextvars
except ModuleNotFoundError:
    contextvars = None  # type: ignore

import concurrent.futures
import contextlib
import dataclasses
import enum
import logging
import os
import pickle
import threading
import time
import typing
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, cast

import ipywidgets as widgets
import reacton
from ipywidgets import DOMWidget, Widget

import solara.server.settings
import solara.util

from . import kernel, websocket
from .. import lifecycle
from .kernel import Kernel, WebsocketStreamWrapper

WebSocket = Any
logger = logging.getLogger("solara.server.app")


class Local(threading.local):
    kernel_context_stack: Optional[List[Optional["VirtualKernelContext"]]] = None


local = Local()


class PageStatus(enum.Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    CLOSED = "closed"


@dataclasses.dataclass
class VirtualKernelContext:
    id: str
    kernel: kernel.Kernel
    # we keep track of the session id to prevent kernel hijacking
    # to 'steal' a kernel, one would need to know the session id
    # *and* the kernel id
    session_id: str
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
    reload: Callable = lambda: None  # noqa: E731
    state: Any = None
    container: Optional[DOMWidget] = None
    # we track which pages are connected to implement kernel culling
    page_status: Dict[str, PageStatus] = dataclasses.field(default_factory=dict)
    # only used for testing
    _last_kernel_cull_task: "Optional[asyncio.Future[None]]" = None
    _last_kernel_cull_future: "Optional[concurrent.futures.Future[None]]" = None
    closed_event: threading.Event = dataclasses.field(default_factory=threading.Event)
    _on_close_callbacks: List[Callable[[], None]] = dataclasses.field(default_factory=list)
    lock: threading.RLock = dataclasses.field(default_factory=threading.RLock)
    event_loop: asyncio.AbstractEventLoop = dataclasses.field(default_factory=asyncio.get_event_loop)

    def __post_init__(self):
        with self:
            for f, *_ in lifecycle._on_kernel_start_callbacks:
                cleanup = f()
                if cleanup:
                    self.on_close(cleanup)

    def restart(self):
        # should we do this, or maybe close the context and create a new one?
        with self:
            for f in reversed(self._on_close_callbacks):
                f()
            self._on_close_callbacks.clear()
            self.__post_init__()

    def display(self, *args):
        print(args)  # noqa

    def on_close(self, f: Callable[[], None]):
        self._on_close_callbacks.append(f)

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
        with self, self.lock:
            for key in self.page_status:
                self.page_status[key] = PageStatus.CLOSED
            if self._last_kernel_cull_task:
                self._last_kernel_cull_task.cancel()
            if self._last_kernel_cull_future:
                self._last_kernel_cull_future.cancel()
            if self.closed_event.is_set():
                logger.error("Tried to close a kernel context that is already closed: %s", self.id)
                return
            logger.info("Shut down virtual kernel: %s", self.id)
            for f in reversed(self._on_close_callbacks):
                f()
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
            self.kernel.close()
            self.kernel = None  # type: ignore
            if self.id in contexts:
                del contexts[self.id]
            del current_context[get_current_thread_key()]
            # We saw in memleak_test that there are sometimes other entries in current_context
            # In which _DummyThread's reference this context, so we remove those references too
            # TODO: Think about what to do with those Threads
            _contexts = current_context.copy()
            for key, _ctx in _contexts.items():
                if _ctx is self:
                    del current_context[key]
            self.closed_event.set()

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

    def page_connect(self, page_id: str):
        if self.closed_event.is_set():
            raise RuntimeError("Cannot connect a page to a closed kernel")
        logger.info("Connect page %s for kernel %s", page_id, self.id)
        with self.lock:
            if self.closed_event.is_set():
                raise RuntimeError("Cannot connect a page to a closed kernel")
            if page_id in self.page_status and self.page_status.get(page_id) == PageStatus.CLOSED:
                raise RuntimeError("Cannot connect a page that is already closed")
            self.page_status[page_id] = PageStatus.CONNECTED
            if self._last_kernel_cull_task:
                logger.info("Cancelling previous kernel cull task for virtual kernel %s", self.id)
                self._last_kernel_cull_task.cancel()

    def _bump_kernel_cull(self):
        async def kernel_cull():
            try:
                cull_timeout_sleep_seconds = solara.util.parse_timedelta(solara.server.settings.kernel.cull_timeout)
                logger.info("Scheduling kernel cull, will wait for max %s before shutting down the virtual kernel %s", cull_timeout_sleep_seconds, self.id)
                await asyncio.sleep(cull_timeout_sleep_seconds)
                logger.info("Timeout reached, checking if we should be shutting down virtual kernel %s", self.id)
                with self.lock:
                    has_connected_pages = PageStatus.CONNECTED in self.page_status.values()
                    if has_connected_pages:
                        logger.info("We have (re)connected pages, keeping the virtual kernel %s alive", self.id)
                    else:
                        logger.info("No connected pages, and timeout reached, shutting down virtual kernel %s", self.id)
                        self.close()
                if current_event_loop is not None and future is not None:
                    try:
                        current_event_loop.call_soon_threadsafe(future.set_result, None)
                    except RuntimeError:
                        pass  # event loop already closed, happens during testing
            except asyncio.CancelledError:
                if current_event_loop is not None and future is not None:
                    try:
                        if sys.version_info >= (3, 9):
                            current_event_loop.call_soon_threadsafe(future.cancel, "cancelled because a new cull task was scheduled")
                        else:
                            current_event_loop.call_soon_threadsafe(future.cancel)
                    except RuntimeError:
                        pass  # event loop already closed, happens during testing
                raise

        async def create_task():
            task = asyncio.create_task(kernel_cull())
            # create a reference to the task so we can cancel it later
            self._last_kernel_cull_task = task
            await task

        with self.lock:
            future: "Optional[asyncio.Future[None]]" = None
            current_event_loop: Optional[asyncio.AbstractEventLoop] = None
            try:
                future = asyncio.Future()
                current_event_loop = asyncio.get_event_loop()
            except RuntimeError:
                pass
            if self._last_kernel_cull_task:
                logger.info("Cancelling previous kernel cull tas for virtual kernel %s", self.id)
                self._last_kernel_cull_task.cancel()

            logger.info("Scheduling kernel cull for virtual kernel %s", self.id)

            async def create_task():
                task = asyncio.create_task(kernel_cull())
                # create a reference to the task so we can cancel it later
                self._last_kernel_cull_task = task
                try:
                    await task
                except RuntimeError:
                    pass  # event loop already closed, happens during testing

            self._last_kernel_cull_future = asyncio.run_coroutine_threadsafe(create_task(), keep_alive_event_loop)
            return future

    def page_disconnect(self, page_id: str) -> "Optional[asyncio.Future[None]]":
        """Signal that a page has disconnected, and schedule a kernel cull if needed.

        During the kernel reconnect window, we will keep the kernel alive, even if all pages have disconnected.

        Will return a future that is set when the kernel cull is done, when an event loop is available.
        The scheduled kernel cull can be cancelled when a new page connects, a new disconnect is scheduled,
        or a page if explicitly closed.
        """

        logger.info("Disconnect page %s for kernel %s", page_id, self.id)
        future: "asyncio.Future[None]" = asyncio.Future()
        with self.lock:
            if self.page_status[page_id] == PageStatus.CLOSED:
                # this happens when the close beackon call happens before the websocket disconnect
                logger.info("Page %s already closed for kernel %s", page_id, self.id)
                future.set_result(None)
                return future
            assert self.page_status[page_id] == PageStatus.CONNECTED, "cannot disconnect a page that is in state: %r" % self.page_status[page_id]
            self.page_status[page_id] = PageStatus.DISCONNECTED
            has_connected_pages = PageStatus.CONNECTED in self.page_status.values()
            if not has_connected_pages:
                # when we have no connected pages, we will schedule a kernel cull
                future = self._bump_kernel_cull()
            else:
                logger.info("Still have connected pages, do nothing for kernel %s", self.id)
                future.set_result(None)
            return future

    def page_close(self, page_id: str):
        """Signal that a page has closed, close the context if needed and schedule a kernel cull if needed.

        Closing the browser tab or a page navigation means an explicit close, which is
        different from a websocket/page disconnect, which we might want to recover from.

        """
        future: "Optional[asyncio.Future[None]]" = None

        try:
            future = asyncio.Future()
        except RuntimeError:
            pass
        else:
            future.set_result(None)

        logger.info("page status: %s", self.page_status)
        with self.lock:
            if self.closed_event.is_set():
                logger.info("Kernel %s was already closed when page %s attempted to close", self.id, page_id)
                return
            if self.page_status[page_id] == PageStatus.CLOSED:
                logger.info("Page %s already closed for kernel %s", page_id, self.id)
                return
            self.page_status[page_id] = PageStatus.CLOSED
            logger.info("Close page %s for kernel %s", page_id, self.id)
            has_connected_pages = PageStatus.CONNECTED in self.page_status.values()
            has_disconnected_pages = PageStatus.DISCONNECTED in self.page_status.values()
            # if we have disconnected pages, we may have cancelled the kernel cull task
            # if we still have connected pages, it will go to a disconnected state again
            # which will also trigger a new kernel cull
            if has_disconnected_pages:
                future = self._bump_kernel_cull()
            if not (has_connected_pages or has_disconnected_pages):
                logger.info("No connected or disconnected pages, shutting down virtual kernel %s", self.id)
                self.close()
            else:
                logger.info("Still have connected or disconnected pages, keeping virtual kernel %s alive", self.id)
        return future


try:
    # Normal Python
    keep_alive_event_loop = asyncio.new_event_loop()

    def _run():
        asyncio.set_event_loop(keep_alive_event_loop)
        try:
            keep_alive_event_loop.run_forever()
        except Exception:
            logger.exception("Error in keep alive event loop")
            raise

    threading.Thread(target=_run, daemon=True).start()
except RuntimeError:
    # Emscripten/pyodide/lite
    keep_alive_event_loop = asyncio.get_event_loop()

contexts: Dict[str, VirtualKernelContext] = {}
# maps from thread key to VirtualKernelContext, if VirtualKernelContext is None, it exists, but is not set as current
current_context: Dict[str, Optional[VirtualKernelContext]] = {}


def create_dummy_context():
    from . import kernel

    kernel_context = VirtualKernelContext(
        id="dummy",
        session_id="dummy",
        kernel=kernel.Kernel(),
    )
    return kernel_context


if contextvars is not None:
    if typing.TYPE_CHECKING:
        async_context_id = contextvars.ContextVar[str]("async_context_id")
    else:
        async_context_id = contextvars.ContextVar("async_context_id")
    async_context_id.set("default")
else:
    async_context_id = None


def get_current_thread_key() -> str:
    if not solara.server.settings.kernel.threaded:
        if async_context_id is not None:
            try:
                key = async_context_id.get()
            except LookupError:
                raise RuntimeError("no kernel context set")
        else:
            raise RuntimeError("No threading support, and no contextvars support (Python 3.6 is not supported for this)")
    else:
        thread = threading.current_thread()
        key = get_thread_key(thread)
    return key


def get_thread_key(thread: threading.Thread) -> str:
    if not solara.server.settings.kernel.threaded:
        if async_context_id is not None:
            return async_context_id.get()
    thread_key = thread._name + str(thread._ident)  # type: ignore
    return thread_key


def set_context_for_thread(context: VirtualKernelContext, thread: threading.Thread):
    key = get_thread_key(thread)
    current_context[key] = context


def clear_context_for_thread(thread: threading.Thread):
    key = get_thread_key(thread)
    current_context.pop(key, None)


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


@contextlib.contextmanager
def without_context():
    context = None
    try:
        context = get_current_context()
    except RuntimeError:
        pass
    thread_key = get_current_thread_key()
    current_context[thread_key] = None
    try:
        yield
    finally:
        current_context[thread_key] = context


def initialize_virtual_kernel(session_id: str, kernel_id: str, websocket: websocket.WebsocketWrapper):
    from solara.server import app as appmodule

    if kernel_id in contexts:
        logger.info("reusing virtual kernel: %s", kernel_id)
        context = contexts[kernel_id]
        if context.session_id != session_id:
            logger.critical("Session id mismatch when reusing kernel (hack attempt?): %s != %s", context.session_id, session_id)
            websocket.send_text("Session id mismatch when reusing kernel (hack attempt?)")
            # to avoid very fast reconnects (we are in a thread anyway)
            time.sleep(0.5)
            raise ValueError("Session id mismatch")
        kernel = context.kernel
    else:
        kernel = Kernel()
        logger.info("new virtual kernel: %s", kernel_id)
        context = contexts[kernel_id] = VirtualKernelContext(id=kernel_id, session_id=session_id, kernel=kernel, control_sockets=[], widgets={}, templates={})

        with context:
            widgets.register_comm_target(kernel)
            appmodule.register_solara_comm_target(kernel)
    with context:
        assert has_current_context()
        assert kernel is Kernel.instance()
        kernel.shell_stream = WebsocketStreamWrapper(websocket, "shell")
        kernel.control_stream = WebsocketStreamWrapper(websocket, "control")
        kernel.session.websockets.add(websocket)
    return context
