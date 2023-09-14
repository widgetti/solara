from unittest.mock import MagicMock

import ipyvuetify as vw

import solara
from solara.lab.components.confirmation_dialog import ConfirmationDialog


def test_confirmation_dialog():
    is_open = solara.reactive(True)
    on_ok = MagicMock()
    el = ConfirmationDialog(is_open, on_ok=on_ok, content="Hello")
    _, rc = solara.render(el, handle_error=False)
    buttons = rc.find(vw.Btn)
    assert len(buttons) == 2
    buttons[0].widget.click()
    assert on_ok.call_count == 1  # was OK button clicked?
    assert not is_open.value  # is dialog closed?
