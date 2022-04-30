import contextlib
import dataclasses
import io
import json
import logging
import os

# import tempfile
import threading
import time
import urllib.request
from typing import IO, Any, Callable, Optional, TypeVar, Union, cast

import react_ipywidgets as react

from solara.datatypes import FileContentResult, Result

logger = logging.getLogger("react-ipywidgets.extra.hooks")
chunk_size_default = 1024**2

__all__ = [
    "use_thread",
    "use_download",
    "use_fetch",
    "use_json_load",
    "use_json",
    "use_file_content",
]
T = TypeVar("T")
U = TypeVar("U")

MaybeResult = Union[T, Result[T]]


def use_retry(*actions: Callable[[], Any]):
    counter, set_counter = react.use_state(0)

    def retry():
        for action in actions:
            action()
        set_counter(lambda counter: counter + 1)

    return counter, retry


def use_thread(callback=Callable[[threading.Event], Any], dependencies=[]):
    def make_event(*_ignore_dependencies):
        return threading.Event()

    cancelled, set_cancelled = react.use_state(False, key="cancelled")
    cancel: threading.Event = react.use_memo(make_event)(dependencies)
    error, set_error = react.use_state(cast(Optional[Exception], None), "error")
    # done, set_done = react.use_state(False, "done")
    # result, set_result = react.use_state(None, key="result")
    result = react.use_ref(None)  # cast(Optional[], None))
    running, set_running = react.use_state(False)
    counter, retry = use_retry(lambda: set_error(None))

    def run():
        if error:
            return
        result.current = None
        set_running(False)
        set_error(None)

        def runner():
            try:
                set_running(True)
                value = callback(cancel)
                result.current = value
                set_running(False)
            except Exception as e:
                set_running(False)
                set_error(e)
                logger.exception(e)
            finally:
                logger.info("thread done!")
                set_running(False)
                if cancel.is_set():
                    set_cancelled(True)

        logger.info("starting thread: %r", runner)
        thread = threading.Thread(target=runner)
        thread.start()

        def cleanup():
            cancel.set()  # cleanup for use effect
            thread.join()

        return cleanup

    react.use_side_effect(run, dependencies + [counter])
    # return result, cancel.set, done, error
    return Result(value=result.current, error=error, cancel=cancel.set, cancelled=cancelled, retry=retry)


def use_download(
    f: MaybeResult[Union[str, os.PathLike, IO]], url, expected_size=None, delay=None, return_content=False, chunk_size=chunk_size_default
) -> Result:
    if not isinstance(f, Result):
        f = Result(value=f)
    assert isinstance(f, Result)
    content_length, set_content_length = react.use_state(expected_size, key="content_length")
    downloaded_length = 0
    file_object = hasattr(f.value, "tell")
    if not file_object:
        file_path = cast(Union[str, os.PathLike], f.value)
        if os.path.exists(file_path) and expected_size is not None:
            file_size = os.path.getsize(file_path)
            if file_size == expected_size:
                downloaded_length = file_size
    downloaded_length, set_downloaded_length = react.use_state(downloaded_length, key="downloaded_length")

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

    result = use_thread(download, [f, url])
    # maybe we wanna check this
    # download_is_done = downloaded_length == content_length

    if content_length is not None:
        progress = downloaded_length / content_length
    else:
        progress = 0

    return dataclasses.replace(result, progress=progress)


def use_fetch(url, chunk_size=chunk_size_default):
    # re-use the same file like object
    f = react.use_memo(lambda *ignore: io.BytesIO(), args=[url])
    result = use_download(f, url, return_content=True, chunk_size=chunk_size)
    print(result.progress)
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

    @react.use_memo
    def read_file(*ignore):
        try:
            with open(path, "rb") as f:
                return f.read()
        except Exception as e:
            return e

    try:
        mtime = os.path.getmtime(path)
    except Exception as e:
        result = FileContentResult[bytes](error=e, retry=retry)
        # result.retry = retry
        return result

    content = read_file(
        path,
        mtime,
        counter,
    )
    if isinstance(content, Exception):
        return FileContentResult[bytes](error=content, retry=retry)
    else:
        return FileContentResult[bytes](value=content, retry=retry)
