import time

import react_ipywidgets as react
from react_ipywidgets import component
from react_ipywidgets import ipywidgets as w
from react_ipywidgets import render_fixed

from .misc import use_download, use_fetch, use_json, use_thread


def test_hook_thread():
    done = False

    @component
    def DownloadFile():
        nonlocal done
        a, _ = react.use_state("a")
        b, _ = react.use_state("b")
        counter, set_counter = react.use_state(0)
        other, set_other = react.use_state(0)
        c, _ = react.use_state("c")
        if counter % 2 == 0:
            set_other(counter)

        def work(cancelled):
            for i in range(256):
                set_counter(i)
                time.sleep(0.001)

        _result, _cancel, done, _error = use_thread(work)
        return w.Label(value=f"{a} {b} {c} {counter}")

    label, rc = render_fixed(DownloadFile())
    expected = "a b c 255"
    for i in range(200):  # max 2 second
        time.sleep(0.01)
        if label.value == expected:
            break
    assert label.value == expected


def test_hook_download(tmpdir):
    url = "https://raw.githubusercontent.com/widgetti/react-ipywidgets/master/.gitignore"
    content_length = 864

    path = tmpdir / "file.txt"

    @component
    def DownloadFile(url=url, expected_size=None):
        progress, done, error, cancel, retry = use_download(path, url, expected_size=expected_size)
        return w.Label(value=f"{progress} {done} {error}")

    label, rc = render_fixed(DownloadFile())
    assert label.value == "0 False None"
    expected = "1.0 True None"
    for i in range(200):  # max 2 second
        time.sleep(0.01)
        if label.value == expected:
            break
    assert label.value == expected

    # if given, content_length, we should render with done immediately
    label, rc = render_fixed(DownloadFile(expected_size=content_length))
    assert label.value == expected

    label, rc = render_fixed(DownloadFile(url=url + ".404"))
    expected = "0 False HTTP Error 404: Not Found"
    for i in range(50):  # max 0.5 second
        time.sleep(0.01)
        if label.value == expected:
            break
    assert label.value == expected


def test_hook_use_fetch():
    url = "https://raw.githubusercontent.com/widgetti/react-ipywidgets/master/.gitignore"
    content_length = 864

    data = error = None

    @component
    def FetchFile(url=url, expected_size=None):
        nonlocal data, error
        data, error = use_fetch(url)
        return w.Label(value=f"{len(data) if data else '-'}")

    label, rc = render_fixed(FetchFile())
    assert label.value == "-"
    expected = f"{content_length}"
    for i in range(200):  # max 2 second
        time.sleep(0.01)
        if label.value == expected:
            break
    assert label.value == expected


def test_hook_use_json():
    url = "https://jherr-pokemon.s3.us-west-1.amazonaws.com/index.json"
    pokemons = 799

    data = error = None

    @component
    def FetchJson(url=url, expected_size=None):
        nonlocal data, error
        data, error = use_json(url)
        return w.Label(value=f"{len(data) if data else '-'}")

    label, rc = render_fixed(FetchJson())
    assert label.value == "-"
    expected = f"{pokemons}"
    for i in range(200):  # max 2 second
        time.sleep(0.01)
        if label.value == expected:
            break
    assert label.value == expected
