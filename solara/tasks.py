import sys
import abc
import asyncio
import dataclasses
import functools
import inspect
import logging
import threading
import warnings
from enum import Enum
import typing
from typing import (
    Any,
    Callable,
    Coroutine,
    Generic,
    List,
    Optional,
    TypeVar,
    Union,
    cast,
    overload,
)
import weakref

import typing_extensions

import solara
import solara.util
from solara.toestand import Singleton
from solara import _using_solara_server

from .toestand import Ref as ref

if sys.version_info >= (3, 8):
    from typing import Literal
else:
    from typing_extensions import Literal


# Import kernel_context for typing only
if typing.TYPE_CHECKING:
    import solara.server.kernel_context


R = TypeVar("R")
T = TypeVar("T")
P = typing_extensions.ParamSpec("P")

logger = logging.getLogger("solara.task")

has_threads = solara.util.has_threads
_main_event_loop: Optional[asyncio.AbstractEventLoop] = None
try:
    # this will be the event loop in Jupyter/IPython
    # on Python >=3.12, get_running_loop() is preferred
    if sys.version_info >= (3, 12):
        _main_event_loop = asyncio.get_running_loop()
    else:
        _main_event_loop = asyncio.get_event_loop()
except RuntimeError:
    pass


def _get_current_task():
    # asyncio.current_task() is not available in Python 3.6
    if sys.version_info >= (3, 7):
        return asyncio.current_task()
    else:
        return asyncio.Task.current_task()


class TaskState(Enum):
    NOTCALLED = 1
    STARTING = 2
    WAITING = 3
    RUNNING = 4
    ERROR = 5
    FINISHED = 6
    CANCELLED = 7


@dataclasses.dataclass(frozen=True)
class TaskResult(Generic[T]):
    value: Optional[T] = None
    latest: Optional[T] = None
    exception: Optional[Exception] = None
    # only useful if you want to know details about the state like STARTING or WAITING
    _state: TaskState = TaskState.NOTCALLED
    progress: Optional[float] = None

    @property
    def not_called(self):
        return self._state == TaskState.NOTCALLED

    @property
    def pending(self):
        return self._state in (TaskState.STARTING, TaskState.WAITING, TaskState.RUNNING)

    @property
    def finished(self):
        return self._state == TaskState.FINISHED

    @property
    def cancelled(self):
        return self._state == TaskState.CANCELLED

    @property
    def error(self):
        return self._state == TaskState.ERROR


class Task(Generic[P, R], abc.ABC):
    def __init__(self, key: str):
        self._result = solara.Reactive(
            TaskResult[R](
                value=None,
                _state=TaskState.NOTCALLED,
            ),
            key="solara.tasks:TaskResult:" + key,
        )
        self._last_value: Optional[R] = None
        self._last_progress: Optional[float] = None
        self._latest = ref(self._result.fields.latest)
        self._value = ref(self._result.fields.value)
        self._error = ref(self._result.fields.error)
        self._finished = ref(self._result.fields.finished)
        self._cancelled = ref(self._result.fields.cancelled)
        self._pending = ref(self._result.fields.pending)
        self._not_called = ref(self._result.fields.not_called)
        self._progress = ref(self._result.fields.progress)
        self._exception = ref(self._result.fields.exception)
        self._state_ = ref(self._result.fields._state)
        # used for tests only
        self._start_event = threading.Event()
        self._start_event.set()

    @property
    def result(self) -> TaskResult[R]:
        return self._result.value

    @property
    def latest(self) -> Optional[R]:
        return self._latest.value

    @property
    def value(self) -> Optional[R]:
        return self._value.value

    @property
    def _state(self) -> TaskState:
        return self._state_.value

    @property
    def error(self) -> bool:
        return self._error.value

    @property
    def finished(self) -> bool:
        return self._finished.value

    @property
    def cancelled(self) -> bool:
        return self._cancelled.value

    @property
    def pending(self) -> bool:
        return self._pending.value

    @property
    def not_called(self) -> bool:
        return self._not_called.value

    @property
    def progress(self) -> Optional[float]:
        return self._progress.value

    @progress.setter
    def progress(self, value: Optional[float]) -> None:
        self._last_progress = value
        self._progress.value = value

    @property
    def exception(self) -> Optional[Exception]:
        return self._exception.value

    @abc.abstractmethod
    def retry(self) -> None: ...

    @abc.abstractmethod
    def cancel(self) -> None: ...

    @abc.abstractmethod
    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> None: ...

    @abc.abstractmethod
    def is_current(self) -> bool: ...

    def _prestart(self):
        self._result.value = TaskResult[R](latest=self._last_value, _state=TaskState.STARTING)


class _CancelledErrorInOurTask(BaseException):
    pass


class TaskAsyncio(Task[P, R]):
    current_task: Optional[asyncio.Task] = None
    current_future: Optional[asyncio.Future] = None
    _cancel: Optional[Callable[[], None]] = None
    _retry: Optional[Callable[[], None]] = None
    _context: Optional["weakref.ReferenceType[solara.server.kernel_context.VirtualKernelContext]"] = None

    def __init__(self, run_in_thread: bool, function: Callable[P, Coroutine[Any, Any, R]], key: str):
        self.run_in_thread = run_in_thread
        self.function = function
        super().__init__(key)

    def cancel(self) -> None:
        if self._cancel:
            self._cancel()
        else:
            raise RuntimeError("Cannot cancel task, never started")

    def retry(self):
        if self._retry:
            self._retry()
        else:
            raise RuntimeError("Cannot retry task, never started")

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> None:
        self._last_progress = None
        current_task: asyncio.Task[None]
        if self.current_task:
            self.current_task.cancel()

        def retry():
            self(*args, **kwargs)

        def cancel():
            event_loop = current_task.get_loop()
            # cancel after cancel is a no-op
            self._cancel = lambda: None
            if _get_current_task() == current_task:
                if event_loop == asyncio.get_event_loop():
                    # we got called in our own task and event loop
                    raise _CancelledErrorInOurTask()
                else:
                    current_task.cancel()
                    self._result.value = TaskResult[R](latest=self._last_value, _state=TaskState.CANCELLED)
            else:
                current_task.cancel()
                self._result.value = TaskResult[R](latest=self._last_value, _state=TaskState.CANCELLED)

        self._cancel = cancel
        self._retry = retry
        if _using_solara_server():
            import solara.server.kernel_context

            context = solara.server.kernel_context.get_current_context()
            self._context = weakref.ref(context)
            call_event_loop = context.event_loop
        else:
            call_event_loop = _main_event_loop or asyncio.get_event_loop()

        self.current_future = future = call_event_loop.create_future()

        if self.run_in_thread:
            thread_event_loop = asyncio.new_event_loop()
            self.current_task = current_task = thread_event_loop.create_task(self._async_run(call_event_loop, future, args, kwargs))

            def runs_in_thread():
                try:
                    thread_event_loop.run_until_complete(current_task)
                except asyncio.CancelledError as e:
                    try:
                        call_event_loop.call_soon_threadsafe(future.set_exception, e)
                    except Exception as e2:
                        if not self._is_context_closed():
                            logger.exception(
                                "error setting exception from for task %s. Original exception: %s\nReason for failing to set exception: %s",
                                self.function.__name__,
                                e,
                                e2,
                            )
                except Exception as e:
                    logger.exception("error running in thread")
                    try:
                        call_event_loop.call_soon_threadsafe(future.set_exception, e)
                    except Exception as e2:
                        if not self._is_context_closed():
                            logger.exception(
                                "error setting exception from for task %s. Original exception: %s\nReason for failing to set exception: %s",
                                self.function.__name__,
                                e,
                                e2,
                            )
                    raise

            self._result.value = TaskResult[R](latest=self._last_value, _state=TaskState.STARTING)
            thread = threading.Thread(target=runs_in_thread, daemon=True)
            thread.start()
        else:
            self.current_task = current_task = asyncio.create_task(self._async_run(call_event_loop, future, args, kwargs))
            self._result.value = TaskResult[R](latest=self._last_value, _state=TaskState.STARTING)

    def is_current(self):
        running_task = self.current_task
        assert running_task is not None
        return (self.current_task == _get_current_task()) and not running_task.cancelled()

    def _is_context_closed(self):
        if self._context is None:
            return False
        context = self._context()
        if context is None:
            return False
        return context.closed_event.is_set()

    async def _async_run(self, call_event_loop: asyncio.AbstractEventLoop, future: asyncio.Future, args, kwargs) -> None:
        self._start_event.wait()

        task_for_this_call = _get_current_task()
        assert task_for_this_call is not None

        if self.is_current():
            self._result.value = TaskResult[R](latest=self._last_value, _state=TaskState.STARTING)

        async def runner():
            try:
                if self.is_current():
                    self._result.value = TaskResult[R](latest=self._last_value, _state=TaskState.RUNNING)
                self._last_value = value = await self.function(*args, **kwargs)
                if self.is_current() and not task_for_this_call.cancelled():  # type: ignore
                    self._result.value = TaskResult[R](value=value, latest=value, _state=TaskState.FINISHED, progress=self._last_progress)
                logger.info("setting result to %r", value)
                try:
                    call_event_loop.call_soon_threadsafe(future.set_result, value)
                except Exception as e:
                    if not self._is_context_closed():
                        logger.exception(
                            "error setting result from for task %s. Original exception: %s\nReason for failing to set result: %s", self.function.__name__, e, e
                        )
                    else:
                        logger.debug(
                            "ignoring error setting result from for task %s. Original exception: %s\nReason for failing to set result: %s",
                            self.function.__name__,
                            e,
                            e,
                        )
            except Exception as e:
                if self.is_current():
                    logger.exception(e)
                    self._result.value = TaskResult[R](latest=self._last_value, exception=e, _state=TaskState.ERROR)
                try:
                    call_event_loop.call_soon_threadsafe(future.set_exception, e)
                except Exception as e2:
                    # we don't know if it is still useful to show this error, so we show it regardless if the context is closed or not
                    logger.exception(
                        "error setting exception from for task %s. Original exception: %s\nReason for failing to set exception: %s",
                        self.function.__name__,
                        e,
                        e2,
                    )
            # Although this seems like an easy way to handle cancellation, an early cancelled task will never execute
            # so this code will never execute, so we need to handle this in the cancel function in __call__
            # except asyncio.CancelledError as e:
            #    if self.is_current():
            #        self._result.value = TaskResult[R](latest=self._last_value, _state=TaskState.CANCELLED)
            #    call_event_loop.call_soon_threadsafe(future.set_exception, e)
            # But... if we call cancel in our own task, we still need to do it from this place
            except _CancelledErrorInOurTask as e:
                try:
                    # maybe there is a different way to get a full stack trace?
                    raise asyncio.CancelledError() from e
                except asyncio.CancelledError as e:
                    if self.is_current():
                        self._result.value = TaskResult[R](latest=self._last_value, _state=TaskState.CANCELLED)
                    call_event_loop.call_soon_threadsafe(future.set_exception, e)

        await runner()


class TaskThreaded(Task[P, R]):
    _current_cancel_event: Optional[threading.Event] = None
    _current_thread: Optional[threading.Thread] = None
    _last_finished_event: Optional[threading.Event] = None
    _cancel: Optional[Callable[[], None]] = None
    _retry: Optional[Callable[[], None]] = None

    def __init__(self, function: Callable[P, R], key: str):
        super().__init__(key)
        self.__qualname__ = function.__qualname__
        self.function = function
        self.lock = threading.Lock()
        self._local = threading.local()

    def cancel(self) -> None:
        if self._cancel:
            self._cancel()
        else:
            raise RuntimeError("Cannot cancel task, never started")

    def retry(self):
        if self._retry:
            self._retry()
        else:
            raise RuntimeError("Cannot retry task, never started")

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> None:
        self._last_finished_event = _last_finished_event = threading.Event()
        self._current_cancel_event = cancel_event = threading.Event()
        self._last_progress = None

        def retry():
            self(*args, **kwargs)

        def cancel():
            cancel_event.set()
            if threading.current_thread() == current_thread:
                raise solara.util.CancelledError()
            self._current_cancel_event = None

        self._retry = retry
        self._cancel = cancel

        with self.lock:
            previous_thread = self._current_thread
            self._current_thread = current_thread = threading.Thread(
                target=lambda: self._run(_last_finished_event, previous_thread, cancel_event, args, kwargs), daemon=False
            )
        self._result.value = TaskResult[R](latest=self._last_value, _state=TaskState.STARTING)
        current_thread.start()

    def is_current(self):
        cancel_event = getattr(self._local, "cancel_event", None)
        if cancel_event is not None and cancel_event.is_set():
            return False
        return self._current_thread == threading.current_thread()

    def _run(self, _last_finished_event, previous_thread: Optional[threading.Thread], cancel_event, args, kwargs) -> None:
        # use_thread has this as default, which can make code run 10x slower
        self._start_event.wait()
        intrusive_cancel = False
        wait_on_previous = False
        self._local.cancel_event = cancel_event

        def runner():
            if wait_on_previous:
                if previous_thread and previous_thread.is_alive():
                    if self.is_current():
                        self._result.value = TaskResult[R](latest=self._last_value, _state=TaskState.WAITING)
                    # don't start before the previous is stopped
                    try:
                        previous_thread.join()
                    except:  # noqa
                        pass
            if self.is_current():
                self._result.value = TaskResult[R](latest=self._last_value, _state=TaskState.RUNNING)
            else:
                # early stop
                return

            callback = self.function
            try:
                guard = solara.util.cancel_guard(cancel_event) if intrusive_cancel else solara.util.nullcontext()
                try:
                    # we only use the cancel_guard context manager around
                    # the function calls to f. We don't want to guard around
                    # a call to react, since that might slow down rendering
                    # during rendering
                    with guard:
                        if self.is_current():
                            value = callback(*args, **kwargs)
                    if inspect.isgenerator(value):
                        generator = value
                        self._last_value = None
                        while True:
                            try:
                                with guard:
                                    self._last_value = value = next(generator)
                                    if self.is_current():
                                        self._result.value = TaskResult[R](latest=value, value=value, _state=TaskState.RUNNING, progress=self._last_progress)
                            except StopIteration:
                                break
                        if self.is_current():
                            self._result.value = TaskResult[R](latest=self._last_value, _state=TaskState.FINISHED, progress=self._last_progress)
                    else:
                        self._last_value = value
                        if self.is_current():
                            self._result.value = TaskResult[R](latest=value, value=value, _state=TaskState.FINISHED, progress=self._last_progress)
                except Exception as e:
                    if self.is_current():
                        logger.exception(e)
                        self._last_value = None
                        self._result.value = TaskResult[R](latest=self._last_value, exception=e, _state=TaskState.ERROR)
                    return
                except solara.util.CancelledError:
                    pass
                    # this means this thread is cancelled not be request, but because
                    # a new thread is running, we can ignore this
            finally:
                if self._current_thread == threading.current_thread():
                    self.running_thread = None
                    logger.info("thread done!")
                    if cancel_event.is_set():
                        self._result.value = TaskResult[R](latest=self._last_value, _state=TaskState.CANCELLED)
                _last_finished_event.set()

        try:
            runner()
        except Exception:
            logger.exception("error running in thread")
            raise


# TODO: Not sure if we want to use this, or have all local variables in Task subclasses be reactive vars
class Proxy:
    def __init__(self, factory):
        self._instance = Singleton(factory)

    def __getattr__(self, name):
        return getattr(self._instance.value, name)

    def __setattr__(self, name, value):
        if name == "_instance":
            super().__setattr__(name, value)
        else:
            setattr(self._instance.value, name, value)

    def __call__(self, *args, **kwargs):
        return self._instance.value(*args, **kwargs)


@overload
def task(
    f: None = None,
    *,
    prefer_threaded: bool = ...,
    check_for_render_context: bool = ...,
) -> Callable[[Callable[P, R]], Task[P, R]]: ...


@overload
def task(
    f: Callable[P, Union[Coroutine[Any, Any, R], R]],
    *,
    prefer_threaded: bool = ...,
    check_for_render_context: bool = ...,
) -> Task[P, R]: ...


def task(
    f: Union[None, Callable[P, Union[Coroutine[Any, Any, R], R]]] = None,
    *,
    prefer_threaded: bool = True,
    check_for_render_context: bool = True,
) -> Union[Callable[[Callable[P, R]], Task[P, R]], Task[P, R]]:
    """Decorator to turn a function or coroutine function into a task.

    Lets you run code in the background, with the UI available to the user. This is useful for long running tasks, like downloading data or processing data.

    The task decorator turns a function or coroutine function (`async def foo(...)` - here foo is called a coroutine function) into a task object.
    A task is a callable that will run the function or coroutine function in a separate thread
    Note that on platforms where threads are supported, asyncio tasks will still be executed in threads (unless the
    `prefer_thread=False` argument is passed). Because a coroutine function might still call long running blocking code.
    Running the asyncio task in a thread will still result in a responsive UI when executed in a separate thread.

    The task object will execute the function only once per virtual kernel and will only store one result per virtual kernel.
    When called multiple times, the previously started thread or asyncio task result will be ignored.

    A running thread or asyncio task can check if it is still the current task by calling `task.is_current()`.
    If `task.is_current()` returns False, the task should stop running and return early.

    The return value of the function is available as the `.value` reactive property on the task object, meaning that if a
    component accesses it, the component will automatically re-run when the value changes, like a [reactive variable](/api/reactive).

    ## Task object

    The task object has the following attributes/values which are all reactive:

    * `.value`: Contains the return value of the function (Only valid if `.finished` is true, else None).
    * `.exception`: The exception raised by the function, if any (Only valid if `.error` is true, else None).
    * `.latest` The last return value of the function, useful for showing out-of-date data while the task is running.
    * `.progress` A readable and writable reactive property which can be used for communicating progress to the user.

    The state of the task can be queried with the following attributes, which are all reactive:

    * `.not_called`: True if the task has not been called yet.
    * `.pending`: True if the task is asked to run, but did not finish yet, did not error and did not get cancelled.
        When true, often a loading or busy indicator is shown to the user.
    * `.finished`: True if the task has finished running. The result is available in the `.value` attribute as
        well as the `.latest` attribute.
    * `.cancelled`: True if the task was cancelled (by calling `.cancel()`).
    * `.error`: True if the function has raised an exception.

    The following methods are available:

    * `(*args, **kwargs)` : Call the task with the given arguments and keyword arguments. The task will only run once per virtual kernel.
    * `.cancel()`: Cancels the task.
    * `is_current()`: Returns True if the task is still the current task, and should continue running.
        Will return False when a new call to the task is made, and this function is being called from the the
        previous thread or asyncio.

    ## State diagram

    The following state diagram shows the possible states of a task and how
    each state transitions to another state.

    ```mermaid
    stateDiagram-v2
        not_called --> pending:  task()
        pending --> finished
        pending --> error: exception
        pending --> pending:  task()
        pending --> cancelled: task.cancel()
        finished --> pending: task()
        error --> pending: task()
        cancelled --> pending: task()
    ```

    Note that calling the task (as indicated by `task()`) can be done from any state.


    ## Example

    ### Async task


    ```solara
    import asyncio
    import solara
    from solara.lab import task

    @task
    async def fetch_data():
        await asyncio.sleep(2)
        return "The answer is 42"

    @solara.component
    def Page():
        solara.Button("Fetch data", on_click=fetch_data)
        solara.ProgressLinear(fetch_data.pending)

        if fetch_data.finished:
            solara.Text(fetch_data.value)
        elif fetch_data.not_called:
            solara.Text("Click the button to fetch data")
        # Optional state check
        # elif fetch_data.cancelled:
        #     solara.Text("Cancelled the fetch")
        # elif fetch_data.error:
        #     solara.Error(str(fetch_data.exception))

    ```

    ### Threaded task

    ```solara
    import time
    import solara
    from solara.lab import task

    @task
    def fetch_data():
        time.sleep(2)
        return "The answer is 42"


    @solara.component
    def Page():
        solara.Button("Fetch data", on_click=fetch_data)
        solara.ProgressLinear(fetch_data.pending)

        if fetch_data.finished:
            solara.Text(fetch_data.value)
        elif fetch_data.not_called:
            solara.Text("Click the button to fetch data")
        # Optional state check
        # elif fetch_data.cancelled:
        #     solara.Text("Cancelled the fetch")
        # elif fetch_data.error:
        #    solara.Error(str(fetch_data.exception))
    ```

    Note that both examples are very similar. In the first example however, we wrap a coroutine function
    which can use `asyncio.sleep`. In the second example, we use a regular function, which uses `time.sleep`.
    If the coroutine function would use `time.sleep` in combination with `prefer_threaded=False`,
    the UI would be unresponsive for 2 seconds.


    ### Showing a progress bar


    Using the `.progress` attribute, you can show a progress bar to the user. This is useful for long running tasks
    but requires a bit more work.

    ```solara
    import time
    import solara
    from solara.lab import task


    @task
    def my_calculation():
        total = 0
        for i in range(10):
            my_calculation.progress = (i + 1) * 10.0
            time.sleep(0.4)
            if not my_calculation.is_current():
                # a new call was made before this call was finished
                return
            total += i**2
        return total


    @solara.component
    def Page():
        solara.Button("Run calculation", on_click=my_calculation)
        solara.ProgressLinear(my_calculation.progress if my_calculation.pending else False)

        if my_calculation.finished:
            solara.Text(f"Calculation result: {my_calculation.value}")
        elif my_calculation.not_called:
            solara.Text("Click the button to fetch data")
        # Optional state check
        # elif my_calculation.cancelled:
        #     solara.Text("Cancelled the fetch")
        # elif my_calculation.error:
        #    solara.Error(str(my_calculation.exception))
    ```

    ### Out-of-date data

    ```solara
    import time
    import solara
    from solara.lab import task


    @task
    def my_calculation():
        total = 0
        for i in range(10):
            time.sleep(0.1)
            total += i**2
        return total


    @solara.component
    def Page():
        solara.ProgressLinear(my_calculation.pending)
        solara.Button("Run simulation", on_click=my_calculation)
        print(my_calculation.pending, my_calculation.value)

        if my_calculation.finished:
            solara.Text(f"Simulation result: {my_calculation.value}")
        if my_calculation.pending and my_calculation.latest:
            solara.Text(f"Simulation previous result: {my_calculation.latest}", style={"opacity": ".3"})
        elif my_calculation.not_called:
            solara.Text("Click the button to fetch data")
    ```

    ## Arguments

    - `f`: Function to turn into task or None
    - `prefer_threaded` - bool: Will run coroutine functions as a task in a thread when threads are available.
        This ensures that even when a coroutine functions calls a blocking function the UI is still responsive.
        On platform where threads are not supported (like Pyodide / WASM / Emscripten / PyScript), a coroutine
        function will always run in the current event loop.
    - `check_for_render_context` - bool: If true, we will check if we are in a render context, and if so, we will
        warn you that you should probably be using `use_task` instead of `task`.

    ```

    """

    def check_if_we_should_use_use_task():
        import reacton.core

        in_reacton_context = reacton.core.get_render_context(required=False) is not None
        if not in_reacton_context:
            # We are not in a reacton context, so we should not (and cannot) use use_task
            return
        from .toestand import _find_outside_solara_frame

        frame = _find_outside_solara_frame()
        if frame is None:
            # We cannot determine which frame we are in, just skip this check
            return
        import inspect

        tb = inspect.getframeinfo(frame)
        msg = """You are calling task(...) from a component, while you should probably be using use_task.

Reason:
- task(...) creates a new task object on every render, and should only be used outside of a component.
- use_task(...) returns the same task object on every render, and should be used inside a component.

Example:
@solara.component
def Page():
    @task  # This is wrong, this creates a new task object on every render
    def my_task():
        ...

Instead, you should do:
@solara.component
def Page():
    @use_task
    def my_task():
        ...

"""
        if tb:
            if tb.code_context:
                code = tb.code_context[0]
            else:
                code = "<No code context available>"
            msg += f"This warning was triggered from:\n{tb.filename}:{tb.lineno}\n{code.strip()}"

        # Check if the call is within a use_memo context by inspecting the call stack
        if frame:
            caller_frame = frame.f_back
            # Check a few frames up the stack (e.g., up to 5) for 'use_memo'
            for _ in range(5):
                if caller_frame is None:
                    break
                func_name = caller_frame.f_code.co_name
                module_name = caller_frame.f_globals.get("__name__", "")
                if func_name == "use_memo" and (module_name.startswith("solara.") or module_name.startswith("reacton.")):
                    # We are in a use_memo (or a context that should not trigger the warning)
                    return
                caller_frame = caller_frame.f_back

        warnings.warn(msg)

    def wrapper(f: Union[None, Callable[P, Union[Coroutine[Any, Any, R], R]]]) -> Task[P, R]:
        if check_for_render_context:
            check_if_we_should_use_use_task()
        # we use wraps to make the key of the reactive variable more unique
        # and less likely to mixup during hot reloads
        assert f is not None
        key = solara.toestand._create_key_callable(f)

        @functools.wraps(f)  # type: ignore
        def create_task():
            if inspect.iscoroutinefunction(f):
                return TaskAsyncio[P, R](prefer_threaded and has_threads, f, key=key)
            else:
                return TaskThreaded[P, R](cast(Callable[P, R], f), key=key)

        return cast(Task[P, R], Proxy(create_task))

    if f is None:
        return wrapper
    else:
        return wrapper(f)


# Quotes around Task[...] are needed in Python <= 3.9, since ParamSpec doesn't properly support non-type arguments
# i.e. [] is taken as a value instead of a type
# See https://github.com/python/typing_extensions/issues/126 and related issues
@overload
def use_task(
    f: None = None,
    *,
    dependencies: Literal[None] = ...,
    raise_error=...,
    prefer_threaded=...,
) -> Callable[[Callable[P, R]], "Task[P, R]"]: ...


@overload
def use_task(
    f: None = None,
    *,
    dependencies: List = ...,
    raise_error=...,
    prefer_threaded=...,
) -> Callable[[Callable[[], R]], "Task[[], R]"]: ...


@overload
def use_task(
    f: Callable[[], R],
    *,
    dependencies: List = ...,
    raise_error=...,
    prefer_threaded=...,
) -> "Task[[], R]": ...


@overload
def use_task(
    f: Callable[P, R],
    *,
    dependencies: Literal[None] = ...,
    raise_error=...,
    prefer_threaded=...,
) -> "Task[P, R]": ...


def use_task(
    f: Union[None, Callable[P, R]] = None,
    *,
    dependencies: Union[None, List] = [],
    raise_error=True,
    prefer_threaded=True,
) -> Union[Callable[[Callable[P, R]], "Task[P, R]"], "Task[P, R]"]:
    """A hook that runs a function or coroutine function as a task and returns the result.

    Allows you to run code in the background, with the UI available to the user. This is useful for long running tasks,
    like downloading data or processing data.

    Unlike with the [`@task`](/api/task) decorator, the result is not globally shared, but only available to the component that called `use_task`.

    Note that unlike the [`@task`](/api/task) decorator, the task is invoked immediately when dependencies are passed. To prevent this, pass `dependencies=None`.


    ## Example

    ### Running in a thread

    ```solara
    import time
    import solara
    from solara.lab import use_task, Task


    @solara.component
    def Page():
        number = solara.use_reactive(4)

        def square():
            time.sleep(1)
            return number.value**2

        result: Task[int] = use_task(square, dependencies=[number.value])

        solara.InputInt("Square", value=number, continuous_update=True)
        if result.finished:
            solara.Success(f"Square of {number} == {result.value}")
        solara.ProgressLinear(result.pending)
    ```

    ### Running in an asyncio task

    Note that the only difference is our function is now a coroutine function,
    and we use `asyncio.sleep` instead of `time.sleep`.

    ```solara
    import asyncio
    import solara
    from solara.lab import use_task, Task


    @solara.component
    def Page():
        number = solara.use_reactive(4)

        async def square():
            await asyncio.sleep(1)
            return number.value**2

        result: Task[int] = use_task(square, dependencies=[number.value])

        solara.InputInt("Square", value=number, continuous_update=True)
        if result.finished:
            solara.Success(f"Square of {number} == {result.value}")
        solara.ProgressLinear(result.pending)
    ```

    ## Arguments

    - `f`: The function or coroutine to run as a task.
    - `dependencies`: A list of dependencies that will trigger a rerun of the task when changed, the task will run automatically execute when the `dependencies=None`
    - `raise_error`: If true, an error in the task will be raised. If false, the error should be handled by the
        user and is available in the `.exception` attribute of the task result object.
    - `prefer_threaded` - bool: Will run coroutine functions as a task in a thread when threads are available.
        This ensures that even when a coroutine functions calls a blocking function the UI is still responsive.
        On platform where threads are not supported (like Pyodide / WASM / Emscripten / PyScript), a coroutine
        function will always run in the current event loop.


    """

    def wrapper(f):
        def create_task() -> "Task[[], R]":
            return task(f, prefer_threaded=prefer_threaded, check_for_render_context=False)

        task_instance = solara.use_memo(create_task, dependencies=[])
        # we always update the function so we do not have stale data in the function
        task_instance.function = f  # type: ignore

        def _prestart():
            if dependencies is not None:
                # we do not want to be in a state of .finished when the dependencies change
                # otherwise user code might render a stale value with the new dependencies
                task_instance._prestart()

        solara.use_memo(_prestart, dependencies=dependencies)

        def run():
            if dependencies is not None:
                # but we only want to execute it as an effect, which makes
                # sure that if the user assigns to a task object, the function f
                # starts after the assignment is executed
                task_instance()

        solara.use_effect(run, dependencies=dependencies)
        if raise_error:
            if task_instance.error:
                assert task_instance.exception is not None
                raise task_instance.exception
        return task_instance

    if f is None:
        return wrapper
    else:
        return wrapper(f)
