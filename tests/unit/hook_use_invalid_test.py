import pytest
import contextlib
import solara.settings

import solara
from solara.validate_hooks import HookValidationError


@contextlib.contextmanager
def hook_check_raise():
    prev = solara.settings.main.check_hooks
    solara.settings.main.check_hooks = "error"
    try:
        yield
    finally:
        solara.settings.main.check_hooks = prev


@contextlib.contextmanager
def hook_check_warn():
    prev = solara.settings.main.check_hooks
    solara.settings.main.check_hooks = "warn"
    try:
        yield
    finally:
        solara.settings.main.check_hooks = prev


def test_hook_use_invalid_loop():
    with hook_check_raise(), pytest.raises(HookValidationError):

        @solara.component
        def Page():
            for i in range(10):
                solara.use_state(1)
            solara.Text("Done")

    with hook_check_warn(), pytest.warns(UserWarning):

        @solara.component
        def Page2():
            for i in range(10):
                solara.use_state(1)
            solara.Text("Done")


def test_hook_use_invalid_conditional():
    with hook_check_warn(), pytest.warns(UserWarning):

        @solara.component
        def Page():
            if 1 > 3:
                solara.use_state(1)
            solara.Text("Done")


def test_hook_use_valid_loop_due_to_noqa():
    # sometimes we know that the use of a hook is stable, even when in a loop

    with hook_check_raise():
        # single line
        @solara.component
        def Page():
            for i in range(10):
                solara.use_state(1)  # noqa
            solara.Text("Done")

        # whole function
        @solara.component
        def Page2():  # noqa
            for i in range(10):
                solara.use_state(1)
            solara.Text("Done")
