import json
import logging
import os
import tempfile
import threading
import time
import urllib.request
from typing import Any, Callable, Optional, cast

import react_ipywidgets as react

logger = logging.getLogger("react-ipywidgets.extra.hooks")


def use_thread(callback=Callable[[threading.Event], Any], dependencies=[]):
    def make_event(*_ignore_dependencies):
        return threading.Event()

    cancel: threading.Event = react.use_memo(make_event)(dependencies)
    error, set_error = react.use_state(cast(Optional[str], None), "error")
    done, set_done = react.use_state(False, "done")
    result, set_result = react.use_state(None, key="result")

    def run():
        set_done(False)
        set_error(None)

        def runner():
            try:
                result = callback(cancel)
                set_result(result)
            except Exception as e:
                set_error(str(e))
                logger.exception(e)
            finally:
                logger.info("thread done!")
                set_done(True)
                if cancel.is_set():
                    set_error("Cancelled")

        logger.info("starting thread: %r", runner)
        thread = threading.Thread(target=runner)
        thread.start()

        def cleanup():
            cancel.set()  # cleanup for use effect
            thread.join()

        return cleanup

    react.use_side_effect(run, dependencies)
    return result, cancel.set, done, error


def use_download(file_path, url, expected_size=None, delay=None):
    content_length, set_content_length = react.use_state(expected_size, key="content_length")
    retry_count, set_retry_count = react.use_state(0, key="retry_count")
    downloaded_length = 0
    if os.path.exists(file_path) and expected_size is not None:
        file_size = os.path.getsize(file_path)
        if file_size == expected_size:
            downloaded_length = file_size
    downloaded_length, set_downloaded_length = react.use_state(downloaded_length, key="downloaded_length")
    download_is_done = downloaded_length == content_length

    def download(cancel: threading.Event):
        nonlocal downloaded_length
        if expected_size is not None and downloaded_length == expected_size:
            return  # we already downloaded, but hooks cannot be conditional

        with open(file_path, "wb") as output_file:
            with urllib.request.urlopen(url) as response:
                content_length = int(response.info()["Content-Length"])
                logger.info("content_length for %r = %r", url, content_length)
                set_content_length(content_length)
                bytes_read = 0
                while not cancel.is_set():
                    chunk = response.read(1024**2 * 1)

                    if delay:
                        time.sleep(delay)
                    if not chunk:
                        break
                    bytes_read += len(chunk)
                    output_file.write(chunk)
                    set_downloaded_length(bytes_read)

    _result, cancel, thread_is_done, error = use_thread(download, [file_path, url, retry_count])

    def retry():
        set_retry_count(retry_count + 1)

    if content_length is not None:
        progress = downloaded_length / content_length
    else:
        progress = 0
    return progress, download_is_done & thread_is_done, error, cancel, retry


def use_fetch(url):
    file, filename = react.use_memo(lambda *ignore: tempfile.mkstemp(), url)()
    progress, download_is_done, error, cancel, retry = use_download(filename, url)

    @react.use_memo
    def read_data(*ignore):
        nonlocal error
        if download_is_done:
            try:
                with open(filename, "rb") as f:
                    data = f.read()
                    f.close()
                # os.close(file)
            except Exception as e:
                error = e
                data = None
            return data

    data = read_data(download_is_done)
    return data, error


def use_json(path):
    data, error = use_fetch(path)

    @react.use_memo
    def read_json(*ignore):
        nonlocal error
        if data and not error:
            try:
                return json.loads(data)
            except Exception as e:
                error = e

    return read_json(data), error
