import contextlib
import dataclasses
import functools
import inspect
import io
import json
import logging
import os
import sys

# import tempfile
import threading
import time
import urllib.request
import uuid
from typing import IO, Any, Callable, Iterator, Optional, Tuple, TypeVar, Union, cast

import solara
from solara.datatypes import FileContentResult, Result, ResultState

logger = logging.getLogger("react-ipywidgets.extra.hooks")
chunk_size_default = 1024**2

__all__ = [
    "use_thread",
    "use_download",
    "use_fetch",
    "use_json_load",
    "use_json",
    "use_file_content",
    "use_uuid4",
    "use_unique_key",
    "use_state_or_update",
    "use_previous",
]
T = TypeVar("T")
U = TypeVar("U")

MaybeResult = Union[T, Result[T]]


# inherit from BaseException so less change of being caught
# in an except
class CancelledError(BaseException):
    pass


def use_retry(*actions: Callable[[], Any]):
    counter, set_counter = solara.use_state(0)

    def retry():
        for action in actions:
            action()
        set_counter(lambda counter: counter + 1)

    return counter, retry


def use_thread(
    callback=Union[
        Callable[[threading.Event], T],
        Iterator[Callable[[threading.Event], T]],
        Callable[[], T],
        Iterator[Callable[[], T]],
    ],
    dependencies=[],
    intrusive_cancel=True,
) -> Result[T]:
    def make_event(*_ignore_dependencies):
        return threading.Event()

    def make_lock():
        return threading.Lock()

    lock: threading.Lock = solara.use_memo(make_lock, [])
    updater = use_force_update()
    result_state, set_result_state = solara.use_state(ResultState.INITIAL)
    error = solara.use_ref(cast(Optional[Exception], None))
    result = solara.use_ref(cast(Optional[T], None))
    running_thread = solara.use_ref(cast(Optional[threading.Thread], None))
    counter, retry = use_retry()
    cancel: threading.Event = solara.use_memo(make_event, [*dependencies, counter])

    @contextlib.contextmanager
    def cancel_guard():
        if not intrusive_cancel:
            yield
            return

        def tracefunc(frame, event, arg):
            # this gets called at least for every line executed
            if cancel.is_set():
                rc = solara.core._get_render_context(required=False)
                # we do not want to cancel the rendering cycle
                if rc is None or not rc._is_rendering:
                    # this will bubble up
                    raise CancelledError()
            # keep tracing:
            return tracefunc

        # see https://docs.python.org/3/library/sys.html#sys.settrace
        # it is for the calling thread only
        # not every Python implementation has it
        prev = None
        if hasattr(sys, "gettrace"):
            prev = sys.gettrace()
        if hasattr(sys, "settrace"):
            sys.settrace(tracefunc)
        try:
            yield
        finally:
            if hasattr(sys, "settrace"):
                sys.settrace(prev)

    def run():
        set_result_state(ResultState.STARTING)

        def runner():
            wait_for_thread = None
            with lock:
                # if there is a current thread already, we'll need
                # to wait for it. copy the ref, and set ourselves
                # as the current one
                if running_thread.current:
                    wait_for_thread = running_thread.current
                running_thread.current = threading.current_thread()
            if wait_for_thread is not None:
                set_result_state(ResultState.WAITING)
                # don't start before the previous is stopped
                try:
                    wait_for_thread.join()
                except:  # noqa
                    pass
                if threading.current_thread() != running_thread.current:
                    # in case a new thread was started that also was waiting for the previous
                    # thread to st stop, we can finish this
                    return
            # we previously set current to None, but if we do not do that, we can still render the old value
            # while we can still show a loading indicator using the .state
            # result.current = None
            set_result_state(ResultState.RUNNING)

            sig = inspect.signature(callback)
            if sig.parameters:
                f = functools.partial(callback, cancel)
            else:
                f = callback
            try:
                try:
                    # we only use the cancel_guard context manager around
                    # the function calls to f. We don't want to guard around
                    # a call to react, since that might slow down rendering
                    # during rendering
                    with cancel_guard():
                        value = f()
                    if inspect.isgenerator(value):
                        while True:
                            try:
                                with cancel_guard():
                                    result.current = next(value)
                                    error.current = None
                            except StopIteration:
                                break
                            # assigning to the ref doesn't trigger a rerender, so do it manually
                            updater()
                        if threading.current_thread() == running_thread.current:
                            set_result_state(ResultState.FINISHED)
                    else:
                        result.current = value
                        error.current = None
                        if threading.current_thread() == running_thread.current:
                            set_result_state(ResultState.FINISHED)
                except Exception as e:
                    error.current = e
                    if threading.current_thread() == running_thread.current:
                        set_result_state(ResultState.ERROR)
                        logger.exception(e)
                    return
                except CancelledError:
                    pass
                    # this means this thread is cancelled not be request, but because
                    # a new thread is running, we can ignore this
            finally:
                if threading.current_thread() == running_thread.current:
                    running_thread.current = None
                    logger.info("thread done!")
                    if cancel.is_set():
                        set_result_state(ResultState.CANCELLED)

        logger.info("starting thread: %r", runner)
        thread = threading.Thread(target=runner, daemon=True)
        thread.start()

        def cleanup():
            cancel.set()  # cleanup for use effect

        return cleanup

    solara.use_side_effect(run, dependencies + [counter])
    return Result[T](value=result.current, error=error.current, state=result_state, cancel=cancel.set, _retry=retry)


def use_download(
    f: MaybeResult[Union[str, os.PathLike, IO]], url, expected_size=None, delay=None, return_content=False, chunk_size=chunk_size_default
) -> Result:
    if not isinstance(f, Result):
        f = Result(value=f)
    assert isinstance(f, Result)
    content_length, set_content_length = solara.use_state(expected_size, key="content_length")
    downloaded_length = 0
    file_object = hasattr(f.value, "tell")
    if not file_object:
        file_path = cast(Union[str, os.PathLike], f.value)
        if os.path.exists(file_path) and expected_size is not None:
            file_size = os.path.getsize(file_path)
            if file_size == expected_size:
                downloaded_length = file_size
    downloaded_length, set_downloaded_length = solara.use_state(downloaded_length, key="downloaded_length")

    def download(cancel: threading.Event):
        assert isinstance(f, Result)
        nonlocal downloaded_length
        if expected_size is not None and downloaded_length == expected_size:
            return  # we already downloaded, but hooks cannot be conditional

        context: Any = None
        if file_object:
            context = contextlib.nullcontext()
            output_file = cast(IO, f.value)
        else:
            # f = cast(Result[Union[str, os.PathLike]], f)
            output_file = context = open(f.value, "wb")  # type: ignore

        with context:
            with urllib.request.urlopen(url) as response:
                content_length = int(response.info()["Content-Length"])
                logger.info("content_length for %r = %r", url, content_length)
                set_content_length(content_length)
                bytes_read = 0
                while not cancel.is_set():
                    chunk = response.read(chunk_size)

                    if delay:
                        time.sleep(delay)
                    if not chunk:
                        break
                    bytes_read += len(chunk)
                    output_file.write(chunk)
                    set_downloaded_length(bytes_read)
        return bytes_read

    result: Result[Any] = use_thread(download, [f, url])
    # maybe we wanna check this
    # download_is_done = downloaded_length == content_length

    if content_length is not None:
        progress = downloaded_length / content_length
    else:
        progress = 0

    return dataclasses.replace(result, progress=progress)


def use_fetch(url, chunk_size=chunk_size_default):
    # re-use the same file like object
    f = solara.use_memo(io.BytesIO, [url])
    result = use_download(f, url, return_content=True, chunk_size=chunk_size)
    return dataclasses.replace(result, value=f.getvalue() if result.progress == 1 else None)


def compose_result(head, *tail):
    return head


def ensure_result(input: MaybeResult[T]) -> Result[T]:
    if isinstance(input, Result):
        return input
    else:
        return Result(value=input)


def make_use_thread(f: Callable[[T], U]):
    def use_result(input: MaybeResult[T]) -> Result[U]:
        input_result = ensure_result(input)

        def in_thread(cancel: threading.Event):
            if input_result.value:
                return f(input_result.value)

        return use_thread(in_thread, dependencies=[input_result.value])

    return use_result


@make_use_thread
def use_json_load(value: bytes):
    return json.loads(value)


def use_json(path):
    return use_fetch(path) | use_json_load


def use_file_content(path, watch=False) -> FileContentResult[bytes]:
    counter, retry = use_retry()

    def read_file(*ignore):
        try:
            with open(path, "rb") as f:
                return f.read()
        except Exception as e:
            return e

    result = None
    try:
        mtime = os.path.getmtime(path)
    except Exception:
        mtime = None

    content = solara.use_memo(read_file, dependencies=[path, mtime, counter])
    if result is not None:
        return result
    if isinstance(content, Exception):
        return FileContentResult[bytes](error=content, _retry=retry)
    else:
        return FileContentResult[bytes](value=content, _retry=retry)


def use_force_update() -> Callable[[], None]:
    """Returns a callable that can be used to force an update of a component.

    This is used when external state has change, and we need to re-render out component.
    """
    _counter, set_counter = solara.use_state(0, "force update counter")

    def updater():
        set_counter(lambda count: count + 1)

    return updater


def use_uuid4(dependencies=[]):
    """Generate a unique string using the uuid4 algorithm. Will only change when the dependencies change."""

    def make_uuid(*_ignore):
        return str(uuid.uuid4())

    return solara.use_memo(make_uuid, dependencies)


def use_unique_key(key: str = None, prefix: str = "", dependencies=[]):
    """Generate a unique string, or use key when not None. Dependencies are forwarded to `use_uuid4`."""
    uuid = use_uuid4(dependencies=dependencies)
    return prefix + (key or uuid)


def use_state_or_update(
    initial_or_updated: T, key: str = None, eq: Callable[[Any, Any], bool] = None
) -> Tuple[T, Callable[[Union[T, Callable[[T], T]]], None]]:
    """This is useful for situations where a prop can change from a parent
    component, which should be respected, and otherwise the internal
    state should be kept.
    """
    value, set_value = solara.use_state(initial_or_updated, key=key, eq=eq)

    def possibly_update():
        nonlocal value
        # only gets called when initial_or_updated changes
        set_value(initial_or_updated)
        # this make sure the return value gets updated directly
        value = initial_or_updated

    solara.use_memo(possibly_update, [initial_or_updated])
    return value, set_value


def use_previous(value: T, condition=True) -> T:
    ref = solara.use_ref(value)

    def assign():
        if condition:
            ref.current = value

    solara.use_effect(assign, [value])
    return ref.current
