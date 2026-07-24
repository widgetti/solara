"""settings.main.gc_freeze: startup state is frozen after the dummy-kernel run.

Freezing moves the permanent startup objects (imports, module-level app state) out
of the garbage collector's scanned generations, keeping later collections
proportional to live session state. It must be on in production (or when forced),
off in development (hot reload would freeze stale app modules into a permanent
leak), and must run only once per process.
"""

import gc
from pathlib import Path

import pytest

import solara.server.app
import solara.server.settings
from solara.server.app import AppScript

HERE = Path(__file__).parent

APP = str(HERE / "solara_test_apps" / "single_file.py")


@pytest.fixture
def freeze_baseline():
    # the flag is process-global; reset it and make sure we never leave the
    # process frozen (frozen objects would be excluded from gc for other tests).
    # Other code in the process may already have frozen objects (seen on CI:
    # a few hundred at test start), so tests assert on the DELTA, not absolutes.
    previous_flag = solara.server.app._gc_frozen
    previous_setting = solara.server.settings.main.gc_freeze
    previous_mode = solara.server.settings.main.mode
    solara.server.app._gc_frozen = False
    try:
        yield gc.get_freeze_count()
    finally:
        gc.unfreeze()
        solara.server.app._gc_frozen = previous_flag
        solara.server.settings.main.gc_freeze = previous_setting
        solara.server.settings.main.mode = previous_mode


def _init_app(no_kernel_context):
    app = AppScript(APP)
    try:
        app.init()
    finally:
        app.close()


@pytest.mark.parametrize(
    "mode, gc_freeze, expect_frozen",
    [
        ("production", None, True),  # auto: on in production
        ("development", None, False),  # auto: off under hot reload
        ("development", True, True),  # explicit override wins
        ("production", False, False),  # explicit opt-out
    ],
)
def test_gc_freeze_gating(freeze_baseline, kernel_context, no_kernel_context, mode, gc_freeze, expect_frozen):
    solara.server.settings.main.mode = mode
    solara.server.settings.main.gc_freeze = gc_freeze
    _init_app(no_kernel_context)
    if expect_frozen:
        assert gc.get_freeze_count() > freeze_baseline
    else:
        assert gc.get_freeze_count() == freeze_baseline


def test_gc_freeze_only_once(freeze_baseline, kernel_context, no_kernel_context):
    solara.server.settings.main.mode = "production"
    solara.server.settings.main.gc_freeze = None
    _init_app(no_kernel_context)
    assert gc.get_freeze_count() > freeze_baseline
    gc.unfreeze()
    # a second app init (e.g. another app on a different route) must not freeze again:
    # by then session objects can exist and freezing them would pin them forever
    _init_app(no_kernel_context)
    assert gc.get_freeze_count() == 0
