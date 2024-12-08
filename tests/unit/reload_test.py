import shutil
from pathlib import Path

import pytest

import solara.lab
import solara.lifecycle
from solara.server import reload
from solara.server.app import AppScript

HERE = Path(__file__).parent

kernel_start_path = HERE / "solara_test_apps" / "kernel_start.py"
app_start_path = HERE / "solara_test_apps" / "app_start.py"


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


@pytest.mark.parametrize("as_module", [False, True])
def test_app_reload(tmpdir, kernel_context, extra_include_path, no_kernel_context, as_module):
    target = Path(tmpdir) / "app_start.py"
    shutil.copy(app_start_path, target)
    with extra_include_path(str(tmpdir)):
        on_app_start_callbacks = solara.lifecycle._on_app_start_callbacks.copy()
        callbacks_start = [k.callback for k in solara.lifecycle._on_app_start_callbacks]
        if as_module:
            app = AppScript(f"{target.stem}")
        else:
            app = AppScript(f"{target}")
        try:
            app.run()
            module = app.routes[0].module
            module.started.assert_called_once()  # type: ignore
            module.cleaned.assert_not_called()  # type: ignore
            callback = module.app_start  # type: ignore
            callbacks = [k.callback for k in solara.lifecycle._on_app_start_callbacks]
            assert callbacks == [*callbacks_start, callback]
            prev = callbacks.copy()
            reload.reloader.reload_event_next.clear()
            target.touch()
            # wait for the event to trigger
            reload.reloader.reload_event_next.wait()
            module.started.assert_called_once()  # type: ignore
            module.cleaned.assert_called_once()  # type: ignore
            # we only 'rerun' after the first run
            app.run()
            module_reloaded = app.routes[0].module
            module.started.assert_called_once()  # type: ignore
            module.cleaned.assert_called_once()  # type: ignore
            module_reloaded.started.assert_called_once()  # type: ignore
            module_reloaded.cleaned.assert_not_called()  # type: ignore
            assert module_reloaded is not module
            callback = module_reloaded.app_start  # type: ignore
            callbacks = [k[0] for k in solara.lifecycle._on_app_start_callbacks]
            assert callbacks != prev
            assert callbacks == [*callbacks_start, callback]
        finally:
            app.close()
            solara.lifecycle._on_app_start_callbacks.clear()
            solara.lifecycle._on_app_start_callbacks.extend(on_app_start_callbacks)
