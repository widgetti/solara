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
from collections import defaultdict
import logging
import os
import pickle
import threading
import time
import typing
from pathlib import Path
from typing import Any, Callable, DefaultDict, Dict, List, Optional, Tuple, Union, cast

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
# same idea, but for `async with ...`
if typing.TYPE_CHECKING:
    async_stack = contextvars.ContextVar[Union[Tuple[Union[None, "VirtualKernelContext"], ...], None]](name="async_stack", default=None)
else:
    async_stack = contextvars.ContextVar("async_stack", default=None)


class PageStatus(enum.Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    CLOSED = "closed"


def _get_or_create_event_loop() -> asyncio.AbstractEventLoop:
    # On Python 3.12+, asyncio.get_event_loop() raises RuntimeError when called
    # from the main thread after asyncio.run() has cleaned up the loop.
    try:
        return asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop


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
    # Per-reactive RLocks guarding lazy initialization of a reactive variable's value in this
    # kernel's user_dicts (see solara.toestand.KernelStore), keyed by storage_key and created on
    # first access. Relies on defaultdict's GIL-atomic create, so concurrent first-access returns
    # the same lock (a no-GIL build could create two, which only risks a benign double-init).
    # Living on the context (rather than on the process-global KernelStore instance) means the
    # same reactive initializing in different kernels uses different locks (no cross-kernel
    # serialization), and they die with the context (no leak).
    init_locks: DefaultDict[str, threading.RLock] = dataclasses.field(default_factory=lambda: defaultdict(threading.RLock))
    # anything we need to attach to the context
    # e.g. for a react app the render context, so that we can store/restore the state
    app_object: Optional[Any] = None
    reload: Callable = lambda: None  # noqa: E731
    state: Any = None
    # per-kernel opt-in state-persistence manager (solara.state.persist.KernelStatePersistence),
    # attached after a successful backend takeover; None when persistence is off. The restore
    # seam in solara.toestand.KernelStore.get() reads it; the server wiring that populates it
    # lands in commit 2 of the state-persistence feature.
    state_persistence: Optional[Any] = None
    # the per-kernel debounced write-behind flush worker (solara.state.KernelFlushWorker),
    # reachable so close()/on_shutdown can drain it OUTSIDE context.lock (the deadlock contract,
    # §5.3) and so a ws reconnect can call new_epoch() on it (§5.5). None when persistence is off.
    state_flush_worker: Optional[Any] = None
    # why this context was closed: "page-close" | "cull" | "superseded" | "server-shutdown" |
    # "evicted" | "unknown". Drives the reason-gated fenced delete (§5.4) and is logged/asserted.
    close_reason: str = "unknown"
    container: Optional[DOMWidget] = None
    # we track which pages are connected to implement kernel culling
    page_status: Dict[str, PageStatus] = dataclasses.field(default_factory=dict)
    # only used for testing
    _last_kernel_cull_task: "Optional[asyncio.Future[None]]" = None
    _last_kernel_cull_future: "Optional[concurrent.futures.Future[None]]" = None
    closed_event: threading.Event = dataclasses.field(default_factory=threading.Event)
    _on_close_callbacks: List[Callable[[], None]] = dataclasses.field(default_factory=list)
    lock: threading.RLock = dataclasses.field(default_factory=threading.RLock)
    event_loop: asyncio.AbstractEventLoop = dataclasses.field(default_factory=_get_or_create_event_loop)

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

    async def __aenter__(self):
        stack = async_stack.get()
        if stack is None:
            stack = ()
        key = get_current_thread_key()
        async_stack.set(stack + (current_context.get(key, None),))
        new_key = get_current_thread_key()
        current_context[new_key] = self

    async def __aexit__(self, *args):
        key = get_current_thread_key()
        assert local.kernel_context_stack is not None
        stack = async_stack.get()
        assert stack is not None
        current_context[key] = stack[-1]
        async_stack.set(stack[:-1])

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

    def _teardown_persistence(self, reason: str) -> None:
        """Drain the flush worker and reason-gate the fenced delete (§5.3/§5.4/§12).

        MUST run BEFORE ``close()`` acquires ``self.lock``: the worker's final flush does backend
        I/O and the delete is a backend call - doing either under ``context.lock`` is the documented
        deadlock (docs/reactive-initialization-lock-deadlock.md). Wrapped so a persistence failure
        never breaks close(). Idempotent (the worker's own close() and manager detach guard reruns).
        """
        worker = self.state_flush_worker
        manager = self.state_persistence
        if worker is None and manager is None:
            return
        import solara.state as solara_state
        from solara.state.stats import log_close

        deleted = False
        try:
            # bounded final flush (flush-and-leave for every reason); manager.close() detaches
            if worker is not None:
                worker.close(timeout=2.0)
            elif manager is not None:
                manager.close()
            # read the owned generation AFTER the final flush (the rejection protocol may have
            # re-taken during it), and only if persistence is still enabled for this kernel
            generation = manager.generation if manager is not None else None
            disabled = manager.disabled if manager is not None else True
            # Reason-gated fenced delete (§5.4): only a genuine tab close removes the hash; every
            # other reason flushes-and-leaves so the TTL (or a later failover) reclaims it - an
            # unconditional delete here would wipe every session on a rolling deploy / superseded
            # takeover / cull (the §12 blocker).
            if reason == "page-close" and generation and not disabled:
                backend = solara_state.get_backend()
                breaker = solara_state.get_breaker()
                if backend is not None and breaker.allow():
                    try:
                        deleted = backend.delete(self.id, generation=generation)
                        breaker.record_success()
                    except Exception:  # noqa
                        breaker.record_failure()
                        logger.exception("failed to delete state for kernel %s on close", self.id)
            log_close(reason, deleted=deleted)
        except Exception:  # noqa
            logger.exception("state persistence teardown failed for kernel %s", self.id)

    def close(self, reason: str = "unknown"):
        # persistence teardown MUST happen before we acquire self.lock (backend I/O; §5.3 deadlock
        # contract). Guard so the first close wins the reason and a double close does not re-flush.
        if not self.closed_event.is_set():
            self.close_reason = reason
            self._teardown_persistence(reason)
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

    def _cull_timeout_seconds(self) -> float:
        """The cull timeout for this kernel (design §5.4).

        With a genuinely *shared* backend and an attached, enabled persistence manager, an
        orphaned (disconnected) kernel need not linger 24h: its state outlives it in the shared
        store, so cull after the shortened ``SOLARA_STATE_ORPHAN_CULL_TIMEOUT``. The memory
        backend (shared=False) and the persistence-off case keep today's ``kernel.cull_timeout`` -
        there shortening would only lose state (state and kernel die together).
        """
        import solara.state as solara_state

        backend = solara_state.get_backend()
        manager = self.state_persistence
        if backend is not None and backend.shared and manager is not None and not manager.disabled:
            return solara.util.parse_timedelta(solara.settings.state.orphan_cull_timeout)
        return solara.util.parse_timedelta(solara.server.settings.kernel.cull_timeout)

    def _bump_kernel_cull(self):
        async def kernel_cull():
            try:
                cull_timeout_sleep_seconds = self._cull_timeout_seconds()
                logger.info("Scheduling kernel cull, will wait for max %s before shutting down the virtual kernel %s", cull_timeout_sleep_seconds, self.id)
                await asyncio.sleep(cull_timeout_sleep_seconds)
                logger.info("Timeout reached, checking if we should be shutting down virtual kernel %s", self.id)
                with self.lock:
                    has_connected_pages = PageStatus.CONNECTED in self.page_status.values()
                if has_connected_pages:
                    logger.info("We have (re)connected pages, keeping the virtual kernel %s alive", self.id)
                else:
                    logger.info("No connected pages, and timeout reached, shutting down virtual kernel %s", self.id)
                    # close() OUTSIDE self.lock: its persistence teardown does backend I/O (§5.3)
                    self.close(reason="cull")
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
        should_close = False
        with self.lock:
            if self.closed_event.is_set():
                logger.info("Kernel %s was already closed when page %s attempted to close", self.id, page_id)
                return future
            if self.page_status[page_id] == PageStatus.CLOSED:
                logger.info("Page %s already closed for kernel %s", page_id, self.id)
                return future
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
                should_close = True
            else:
                logger.info("Still have connected or disconnected pages, keeping virtual kernel %s alive", self.id)
        if should_close:
            # a genuine tab close: close() OUTSIDE self.lock (persistence teardown does backend
            # I/O, §5.3) with reason="page-close" so the fenced delete removes the hash (§5.4)
            logger.info("No connected or disconnected pages, shutting down virtual kernel %s", self.id)
            self.close(reason="page-close")
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
    # consider renaming this to get_current_context_key
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
        # this signals we are using `async with context`, which means we are interested in task-local context
        stack = async_stack.get()
        if stack is not None and len(stack) > 0:
            current_task = asyncio.current_task()
            if current_task is not None:
                task_key = current_task.get_name()
                key = f"{key}-task:{task_key}"
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


# guards the check-and-reserve of a context slot in initialize_virtual_kernel (§5.1). It is
# deliberately NOT held across the backend takeover I/O: the slot is reserved first, then the
# takeover runs off-lock (no backend I/O under any lock).
_init_lock = threading.Lock()

# takeovers run on this pool so a slow/hung backend cannot block the connect path past the hard
# deadline (§5.1); a hung future keeps running and its late completion fenced-deletes the hash.
_takeover_executor: "Optional[concurrent.futures.ThreadPoolExecutor]" = None
_takeover_executor_lock = threading.Lock()


def _get_takeover_executor() -> "concurrent.futures.ThreadPoolExecutor":
    global _takeover_executor
    if _takeover_executor is None:
        with _takeover_executor_lock:
            if _takeover_executor is None:
                _takeover_executor = concurrent.futures.ThreadPoolExecutor(thread_name_prefix="solara-state-takeover")
    return _takeover_executor


def _has_connected_page(context: VirtualKernelContext) -> bool:
    # lock-free snapshot read (§5.3): the flush worker calls this off the hot path
    return PageStatus.CONNECTED in tuple(context.page_status.values())


def _restore_on_connect(context: VirtualKernelContext, backend, session_id: str) -> None:
    """Run the atomic backend takeover for a fresh context and attach persistence (§5.1/§5.3).

    Never blocks past ``state.connect_timeout`` and never raises: any failure degrades to today's
    behavior (a fresh, unpersisted kernel). Called OUTSIDE ``_init_lock`` (backend I/O).
    """
    import solara.state as solara_state
    from solara.state.stats import log_restore

    breaker = solara_state.get_breaker()
    kernel_id = context.id
    shmac = solara_state.session_hmac(session_id)
    schema_tag = solara_state.effective_schema_tag()
    stats = solara_state.stats()

    # breaker gates restores too (§5.3): during a brownout, skip the takeover read instantly
    # instead of paying the deadline on every connect of a deploy herd.
    if not breaker.allow():
        stats.incr("restore_attempts")
        log_restore("timeout", kernel=kernel_id)
        logger.info("state restore skipped for kernel %s (circuit breaker open)", kernel_id)
        return

    timeout = float(solara.settings.state.connect_timeout)
    future = _get_takeover_executor().submit(backend.takeover, kernel_id, shmac, schema_tag)
    try:
        result = future.result(timeout=timeout)
    except concurrent.futures.TimeoutError:
        # claim-or-delete (§5.1/§12 zombie fix): we degrade to an unpersisted kernel now, but the
        # takeover already bumped (or will bump) the generation in the backend. Leaving the hash
        # readable would let a LATER failover silently roll the user back to this pre-timeout
        # snapshot after they diverged. So when the late takeover finally completes, use its result
        # ONLY to fenced-delete the hash (fire-and-forget on the executor thread that completes it).
        breaker.record_failure()
        stats.incr("restore_attempts")
        stats.record_backend_error("takeover timeout")
        log_restore("timeout", kernel=kernel_id)

        def _claim_or_delete(fut: "concurrent.futures.Future") -> None:
            try:
                res = fut.result()
            except Exception:  # noqa
                return
            if res.reason in ("restored", "miss", "schema-reset") and res.generation:
                try:
                    backend.delete(kernel_id, generation=res.generation)
                except Exception:  # noqa
                    logger.exception("late takeover claim-or-delete failed for kernel %s", kernel_id)

        future.add_done_callback(_claim_or_delete)
        return
    except Exception:  # noqa
        breaker.record_failure()
        stats.incr("restore_attempts")
        stats.record_backend_error("takeover raised")
        log_restore("timeout", kernel=kernel_id)
        logger.exception("state takeover raised for kernel %s", kernel_id)
        return

    breaker.record_success()
    if result.generation == 0:  # identity-mismatch (§5.1) - mirrors the in-memory hijack guard
        stats.incr("restore_attempts")
        logger.warning("state takeover identity mismatch for kernel %s (session hijack?); serving unpersisted", kernel_id)
        return

    try:
        manager = solara_state.attach(
            context,
            backend,
            session_hmac=shmac,
            schema_tag=schema_tag,
            generation=result.generation,
            envelopes=result.fields,
            restore_reason=result.reason,
        )
    except Exception:  # noqa - e.g. PersistKeyError from an unresolved class-body persist=True
        logger.exception("state attach failed for kernel %s; serving unpersisted", kernel_id)
        return

    if manager.recovery_failed:
        # all-or-nothing bail-out happened inside attach (§4.3): keep the manager (it exposes the
        # recovery-failed state for a future canRecover:false) but do NOT start a worker - the
        # kernel runs fresh.
        return

    worker = solara_state.KernelFlushWorker(
        manager,
        breaker=breaker,
        has_connected_page=lambda: _has_connected_page(context),
        on_superseded=lambda: context.close(reason="superseded"),
    )
    context.state_flush_worker = worker
    worker.start()


def _reuse_context_is_stale(context: VirtualKernelContext, backend) -> bool:
    """Whether a reused in-memory context has been superseded in the shared backend (§5.1).

    A fast double reconnect can land back on an instance whose old context is still alive after
    another instance took over in between; resuming it blindly would roll the user back. Compare
    the remembered generation with the backend's. On a peek failure or an open breaker, serve
    in-memory (the documented TOCTOU closure: the fenced write path catches real mismatches).
    Never raises. Called OUTSIDE ``_init_lock`` (backend I/O).
    """
    import solara.state as solara_state

    manager = context.state_persistence
    if manager is None or manager.disabled:
        return False
    breaker = solara_state.get_breaker()
    if not breaker.allow():
        return False
    try:
        # The redis backend builds its client with socket_timeout/socket_connect_timeout set to
        # state.connect_timeout, so peek_generation (a single HGET) is bounded at the client level
        # even on the reuse branch - a hung Redis cannot block the reconnect path. The breaker
        # additionally bounds sustained brownouts.
        stored = backend.peek_generation(context.id)
        breaker.record_success()
    except Exception:  # noqa
        breaker.record_failure()
        logger.exception("peek_generation failed for kernel %s; serving in-memory", context.id)
        return False
    if stored is None:
        return False
    return stored != manager.generation


def _wire_kernel_streams(context: VirtualKernelContext, websocket: websocket.WebsocketWrapper) -> None:
    with context:
        assert has_current_context()
        assert context.kernel is Kernel.instance()
        context.kernel.shell_stream = WebsocketStreamWrapper(websocket, "shell")
        context.kernel.control_stream = WebsocketStreamWrapper(websocket, "control")
        context.kernel.session.websockets.add(websocket)


def initialize_virtual_kernel(session_id: str, kernel_id: str, websocket: websocket.WebsocketWrapper):
    from solara.server import app as appmodule
    import solara.state as solara_state

    backend = solara_state.get_backend()

    # Reserve or find the context slot under a small lock (no backend I/O here, §5.1). A brand-new
    # context is created and registered immediately - the slot is "reserved" - so a concurrent
    # reconnect for the same kernel finds it via the reuse branch (its state_persistence is still
    # None then -> not stale) instead of racing a second takeover, while the takeover I/O itself
    # runs off-lock below.
    with _init_lock:
        context = contexts.get(kernel_id)
        mismatch = context is not None and context.session_id != session_id
        newly_created = False
        if context is None:
            kernel = Kernel()
            logger.info("new virtual kernel: %s", kernel_id)
            context = contexts[kernel_id] = VirtualKernelContext(
                id=kernel_id, session_id=session_id, kernel=kernel, control_sockets=[], widgets={}, templates={}
            )
            newly_created = True

    if mismatch:
        assert context is not None
        logger.critical("Session id mismatch when reusing kernel (hack attempt?): %s != %s", context.session_id, session_id)
        websocket.send_text("Session id mismatch when reusing kernel (hack attempt?)")
        # to avoid very fast reconnects (we are in a thread anyway)
        time.sleep(0.5)
        raise ValueError("Session id mismatch")

    if newly_created:
        with context:
            widgets.register_comm_target(context.kernel)
            appmodule.register_solara_comm_target(context.kernel)
        if backend is not None:
            _restore_on_connect(context, backend, session_id)
    else:
        # reuse branch (§5.1): verify ownership against the shared backend before serving
        if backend is not None and context.state_persistence is not None and _reuse_context_is_stale(context, backend):
            logger.info("virtual kernel %s superseded (generation mismatch); recreating with a fresh takeover", kernel_id)
            # close the stale context (flush-and-leave; backend I/O, so OUTSIDE _init_lock), which
            # frees the slot, then recurse to run the normal atomic takeover + restore.
            context.close(reason="superseded")
            return initialize_virtual_kernel(session_id, kernel_id, websocket)
        logger.info("reusing virtual kernel: %s", kernel_id)
        worker = context.state_flush_worker
        if worker is not None:
            # a genuine client reconnect starts a new connection epoch: reset the one-re-takeover
            # budget of the rejection protocol (§5.5)
            worker.new_epoch()

    _wire_kernel_streams(context, websocket)
    return context
