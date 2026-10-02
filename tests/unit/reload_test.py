import shutil
from pathlib import Path
from typing import List

import pytest

import solara.lab
import solara.lifecycle
from solara.server import reload
from solara.server.app import AppScript

HERE = Path(__file__).parent

kernel_start_path = HERE / "solara_test_apps" / "kernel_start.py"


@pytest.mark.parametrize("as_module", [False, True])
def test_script_reload_component(tmpdir, kernel_context, extra_include_path, no_kernel_context, as_module):
    target = Path(tmpdir) / "kernel_start.py"
    shutil.copy(kernel_start_path, target)
    with extra_include_path(str(tmpdir)):
        on_kernel_start_callbacks = solara.lifecycle._on_kernel_start_callbacks.copy()
        callbacks_start = [k.callback for k in solara.lifecycle._on_kernel_start_callbacks]
        if as_module:
            app = AppScript(f"{target.stem}")
        else:
            app = AppScript(f"{target}")
        app.init()
        try:
            app.run()
            callback = app.routes[0].module.test_callback  # type: ignore
            callbacks = [k.callback for k in solara.lifecycle._on_kernel_start_callbacks]
            assert callbacks == [*callbacks_start, callback]
            prev = callbacks.copy()
            reload.reloader.reload_event_next.clear()
            target.touch()
            # wait for the event to trigger
            reload.reloader.reload_event_next.wait()
            app.run()
            callback = app.routes[0].module.test_callback  # type: ignore
            callbacks = [k[0] for k in solara.lifecycle._on_kernel_start_callbacks]
            assert callbacks != prev
            assert callbacks == [*callbacks_start, callback]
        finally:
            app.close()
            solara.lifecycle._on_kernel_start_callbacks.clear()
            solara.lifecycle._on_kernel_start_callbacks.extend(on_kernel_start_callbacks)


def test_on_kernel_start_cleanup(kernel_context, no_kernel_context):
    def test_callback_cleanup():
        pass

    cleanup = solara.lab.on_kernel_start(test_callback_cleanup)
    assert test_callback_cleanup in [k.callback for k in solara.lifecycle._on_kernel_start_callbacks]
    cleanup()
    assert test_callback_cleanup not in [k.callback for k in solara.lifecycle._on_kernel_start_callbacks]


@pytest.fixture
def reloader_spy(tmpdir):
    """A watched file, plus a list of what reached the app's on_change; restores the global reloader afterwards."""
    reloader = reload.reloader
    saved = reloader.file_handlers.copy(), reloader.on_change, reloader.requires_reload
    app_changes: List[str] = []
    reloader.on_change = app_changes.append
    reloader.requires_reload = False
    path = Path(tmpdir) / "data.txt"
    path.write_text("1")
    try:
        yield path, app_changes
    finally:
        reloader.file_handlers, reloader.on_change, reloader.requires_reload = saved


def test_watch_file_on_change(reloader_spy):
    path, app_changes = reloader_spy
    handled: List[Path] = []
    reload.watch_file(path, on_change=handled.append)
    reload.reloader._on_change(str(path))
    assert handled == [path]
    assert not reload.reloader.requires_reload
    assert app_changes == []


def test_watch_file_reload(reloader_spy):
    path, app_changes = reloader_spy
    reload.watch_file(path)
    reload.reloader._on_change(str(path))
    assert reload.reloader.requires_reload
    assert app_changes == [str(path)]


def test_watch_file_without_on_change_keeps_handler(reloader_spy):
    path, app_changes = reloader_spy
    handled: List[Path] = []
    reload.watch_file(path, on_change=handled.append)
    reload.watch_file(path)
    reload.reloader._on_change(str(path))
    assert handled == [path]
    assert not reload.reloader.requires_reload
    assert app_changes == []
