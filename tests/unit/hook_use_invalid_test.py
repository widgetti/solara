import pytest

import solara
from solara.validate_hooks import HookValidationError


def test_hook_use_invalid_loop():
    with pytest.raises(HookValidationError):

        @solara.component
        def Page():
            for i in range(10):
                solara.use_state(1)
            solara.Text("Done")


def test_hook_use_invalid_conditional():
    with pytest.raises(HookValidationError):

        @solara.component
        def Page():
            if 1 > 3:
                solara.use_state(1)
            solara.Text("Done")
