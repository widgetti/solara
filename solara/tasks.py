import abc
import asyncio
import inspect
import logging
import threading
from typing import (
    Any,
    Callable,
    Coroutine,
    Generic,
    Optional,
    TypeVar,
    Union,
    cast,
    overload,
)

import typing_extensions

import solara
import solara.util
from solara.toestand import Singleton

R = TypeVar("R")

P = typing_extensions.ParamSpec("P")
logger = logging.getLogger("solara.task")


class Task(Generic[P, R], abc.ABC):
    def __init__(self):
        self.result = solara.reactive(
            solara.Result[R](
                value=None,
                state=solara.ResultState.INITIAL,
            )
        )
        self.last_value: Optional[R] = None

    def reset(self):
        self.running_thread = None
        self.cancel()

    @property
    def value(self) -> Optional[R]:
        return self.result.value.value if self.result.value is not None else None

    @property
    def state(self) -> solara.ResultState:
        return self.result.value.state if self.result.value is not None else solara.ResultState.INITIAL

    @property
    def error(self) -> Optional[Exception]:
        return self.result.value.error if self.result.value is not None else None

    def retry(self):
        if self.result.value is not None:
            self.result.value.retry()

    @abc.abstractmethod
    def cancel(self) -> None:
        ...

    @abc.abstractmethod
    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> None:
        ...


class TaskAsyncio(Task[P, R]):
    current_task: Optional[asyncio.Task] = None
    _cancel: Optional[Callable[[], None]] = None

    def __init__(self, function: Callable[P, Coroutine[Any, Any, R]]):
        self.function = function
        super().__init__()

    def cancel(self) -> None:
        if self._cancel:
            self._cancel()
            self._cancel = None

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> None:
        task_for_this_call = None
        previous_task = self.current_task

        def retry():
            self.__call__(*args, **kwargs)

        def cancel():
            assert task_for_this_call is not None
            if asyncio.current_task() == task_for_this_call:
                raise asyncio.CancelledError()
            else:
                task_for_this_call.cancel()
                self.result.value = solara.Result[R](value=self.last_value, state=solara.ResultState.CANCELLED, **common)

        common: _CommonArgs = {
            "cancel": cancel,
            "_retry": retry,
        }
        self._cancel = cancel
        self.result.value = solara.Result[R](value=self.last_value, state=solara.ResultState.STARTING, **common)

        def am_i_the_last_called_task():
            return self.current_task == task_for_this_call

        async def runner():
            try:
                self.result.value = solara.Result[R](value=self.last_value, state=solara.ResultState.RUNNING, **common)
                if previous_task is not None:
                    try:
                        previous_task.cancel()
                        await previous_task
                    except asyncio.CancelledError:
                        pass
                self.last_value = await self.function(*args, **kwargs)
                if am_i_the_last_called_task():
                    self.result.value = self.result.value = solara.Result[R](value=self.last_value, state=solara.ResultState.FINISHED, **common)
            except Exception as e:
                if am_i_the_last_called_task():
                    self.result.value = self.result.value = solara.Result[R](value=self.last_value, error=e, state=solara.ResultState.ERROR, **common)
            except asyncio.CancelledError:
                if am_i_the_last_called_task():
                    self.result.value = self.result.value = solara.Result[R](value=self.last_value, state=solara.ResultState.CANCELLED, **common)

        self.current_task = task_for_this_call = asyncio.create_task(runner())


class TaskThreaded(Task[P, R]):
    _current_cancel_event: Optional[threading.Event] = None
    current_thread: Optional[threading.Thread] = None
    running_thread: Optional[threading.Thread] = None
    _last_finished_event: Optional[threading.Event] = None

    def __init__(self, function: Callable[P, R]):
        super().__init__()
        self.__qualname__ = function.__qualname__
        self.function = function
        self.lock = threading.Lock()

    def cancel(self) -> None:
        if self._current_cancel_event is not None:
            self._current_cancel_event.set()
            if threading.current_thread() == self.running_thread:
                raise solara.util.CancelledError()

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> None:
        self._last_finished_event = _last_finished_event = threading.Event()
        self.current_thread = current_thread = threading.Thread(target=lambda: self._run(_last_finished_event, *args, **kwargs), daemon=True)

        def retry():
            self._run(_last_finished_event, *args, **kwargs)

        common: _CommonArgs = {
            "cancel": self.cancel,
            "_retry": retry,
        }
        self.result.value = solara.Result[R](value=self.last_value, state=solara.ResultState.STARTING, **common)
        current_thread.start()

    def _run(self, _last_finished_event, *args: P.args, **kwargs: P.kwargs) -> None:
        def retry():
            self.__call__(*args, **kwargs)

        # used for testing
        self._current_cancel_event = cancel_event = threading.Event()
        common: _CommonArgs = {
            "cancel": self.cancel,
            "_retry": retry,
        }

        def am_i_the_last_called_thread():
            return self.running_thread == threading.current_thread()

        def runner():
            intrusive_cancel = True
            wait_for_thread = None
            with self.lock:
                # if there is a current thread already, we'll need
                # to wait for it. copy the ref, and set ourselves
                # as the current one
                if self.running_thread:
                    wait_for_thread = self.running_thread
                self.running_thread = threading.current_thread()
            if wait_for_thread is not None:
                self.result.value = solara.Result[R](value=self.last_value, state=solara.ResultState.WAITING, **common)
                # don't start before the previous is stopped
                try:
                    wait_for_thread.join()
                except:  # noqa
                    pass
                if threading.current_thread() != self.running_thread:
                    # in case a new thread was started that also was waiting for the previous
                    # thread to st stop, we can finish this
                    return
            # we previously set current to None, but if we do not do that, we can still render the old value
            # while we can still show a loading indicator using the .state
            # result.current = None
            self.result.value = solara.Result[R](value=self.last_value, state=solara.ResultState.RUNNING, **common)

            callback = self.function
            try:
                guard = solara.util.cancel_guard(cancel_event) if intrusive_cancel else solara.util.nullcontext()
                try:
                    # we only use the cancel_guard context manager around
                    # the function calls to f. We don't want to guard around
                    # a call to react, since that might slow down rendering
                    # during rendering
                    with guard:
                        value = callback(*args, **kwargs)
                    if inspect.isgenerator(value):
                        generator = value
                        self.last_value = None
                        while True:
                            try:
                                with guard:
                                    self.last_value = next(generator)
                                    self.result.value = self.result.value = solara.Result[R](value=self.last_value, state=solara.ResultState.RUNNING, **common)
                            except StopIteration:
                                break
                        if am_i_the_last_called_thread():
                            self.result.value = self.result.value = solara.Result[R](value=self.last_value, state=solara.ResultState.FINISHED, **common)
                    else:
                        self.last_value = None
                        self.last_value = value
                        if am_i_the_last_called_thread():
                            self.result.value = self.result.value = solara.Result[R](value=self.last_value, state=solara.ResultState.FINISHED, **common)
                except Exception as e:
                    if am_i_the_last_called_thread():
                        logger.exception(e)
                        self.result.value = self.result.value = solara.Result[R](value=self.last_value, error=e, state=solara.ResultState.ERROR, **common)
                    return
                except solara.util.CancelledError:
                    pass
                    # this means this thread is cancelled not be request, but because
                    # a new thread is running, we can ignore this
            finally:
                _last_finished_event.set()
                if am_i_the_last_called_thread():
                    self.running_thread = None
                    logger.info("thread done!")
                    if cancel_event.is_set():
                        self.result.value = solara.Result[R](value=self.last_value, state=solara.ResultState.CANCELLED, **common)

        runner()


class _CommonArgs(typing_extensions.TypedDict):
    cancel: Callable[[], None]
    _retry: Callable[[], None]


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


# TODO: coroutine typing
@overload
def task(
    function: None = None,
) -> Callable[[Callable[P, R]], Task[P, R]]:
    ...


@overload
def task(
    function: Callable[P, R],
) -> Task[P, R]:
    ...


def task(
    function: Union[None, Callable[P, Union[Coroutine[Any, Any, R], R]]] = None,
) -> Union[Callable[[Callable[P, R]], Task[P, R]], Task[P, R]]:
    """Decorator to turn a function or coroutine function into a task.

    A task is a callable that will run the function in a separate thread for normal functions
    or a asyncio task for a coroutine function.

    The task callable does only execute the function once when called multiple times,
    and will cancel previous executions if the function is called again before the previous finished.

    The wrapped function return value is available as the `.value` attribute of the task object.

    ## Example

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
        solara.ProgressLinear(fetch_data.state == solara.ResultState.RUNNING)
        if fetch_data.state == solara.ResultState.FINISHED:
            solara.Text(fetch_data.value)
    ```

    """

    def wrapper(func: Union[None, Callable[P, Union[Coroutine[Any, Any, R], R]]]) -> Task[P, R]:
        def create_task():
            if inspect.iscoroutinefunction(function):
                return TaskAsyncio[P, R](function)
            else:
                return TaskThreaded[P, R](cast(Callable[P, R], function))

        return cast(Task[P, R], Proxy(create_task))

    if function is None:
        return wrapper
    else:
        return wrapper(function)


@overload
def use_task(
    f: None = None,
) -> Callable[[Callable[[], R]], solara.Result[R]]:
    ...


@overload
def use_task(
    f: Callable[P, R],
) -> solara.Result[R]:
    ...


def use_task(
    f: Union[None, Callable[[], R]] = None, dependencies=[], *, raise_error=True
) -> Union[Callable[[Callable[[], R]], solara.Result[R]], solara.Result[R]]:
    """Run a function or coroutine as a task and return the result.

    ## Example

    ### Running in a thread

    ```solara
    import time
    import solara
    from solara.lab import use_task


    @solara.component
    def Page():
        number = solara.use_reactive(4)

        def square():
            time.sleep(1)
            return number.value**2

        result: solara.Result[bool] = use_task(square, dependencies=[number.value])

        solara.InputInt("Square", value=number, continuous_update=True)
        if result.state == solara.ResultState.FINISHED:
            solara.Success(f"Square of {number} == {result.value}")
        solara.ProgressLinear(result.state == solara.ResultState.RUNNING)
    ```

    ### Running in a asyncio task

    Note that the only difference is our function is now a coroutine function,
    and we use `asyncio.sleep` instead of `time.sleep`.
    ```solara
    import asyncio
    import solara
    from solara.lab import use_task


    @solara.component
    def Page():
        number = solara.use_reactive(4)

        async def square():
            await asyncio.sleep(1)
            return number.value**2

        result: solara.Result[bool] = use_task(square, dependencies=[number.value])

        solara.InputInt("Square", value=number, continuous_update=True)
        if result.state == solara.ResultState.FINISHED:
            solara.Success(f"Square of {number} == {result.value}")
        solara.ProgressLinear(result.state == solara.ResultState.RUNNING)
    ```

    ## Arguments

    - `f`: The function or coroutine to run as a task.
    - `dependencies`: A list of dependencies that will trigger a rerun of the task when changed.
    - `raise_error`: If true, an error in the task will be raised. If false, the error should be handled by the
        user and is available in the `.error` attribute of the task object.


    """

    def wrapper(f):
        task_instance = solara.use_memo(lambda: task(f), dependencies=dependencies)

        def run():
            task_instance()
            return task_instance.cancel

        solara.use_effect(run, dependencies=dependencies)
        if raise_error:
            if task_instance.state == solara.ResultState.ERROR and task_instance.error is not None:
                raise task_instance.error
        return task_instance.result.value

    if f is None:
        return wrapper
    else:
        return wrapper(f)
