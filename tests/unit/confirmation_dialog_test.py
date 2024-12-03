from unittest.mock import MagicMock

import ipyvuetify as vw

import solara
from solara.lab.components.confirmation_dialog import ConfirmationDialog


def test_confirmation_dialog_ok():
    is_open = solara.reactive(True)
    on_ok = MagicMock()
    on_close = MagicMock()
    el = ConfirmationDialog(is_open, on_ok=on_ok, on_close=on_close, content="Hello")
    _, rc = solara.render(el, handle_error=False)
    buttons = rc.find(vw.Btn)
    assert len(buttons) == 2
    buttons[1].widget.click()
    assert on_ok.call_count == 1  # was OK button clicked?
    assert on_close.call_count == 1  # always triggered
    assert not is_open.value  # is dialog closed?


def test_confirmation_dialog_cancel():
    is_open = solara.reactive(True)
    on_ok = MagicMock()
    on_close = MagicMock()
    el = ConfirmationDialog(is_open, on_ok=on_ok, on_close=on_close, content="Hello")
    _, rc = solara.render(el, handle_error=False)
    buttons = rc.find(vw.Btn)
    assert len(buttons) == 2
    buttons[0].widget.click()
    assert on_ok.call_count == 0  # on_ok action should not have been executed
    assert on_close.call_count == 1  # always triggered
    assert not is_open.value  # is dialog closed?


def test_confirm_external_close():
    # e.g. when persistent=False, clicking away from the dialog closes it
    is_open = solara.reactive(True)
    on_ok = MagicMock()
    on_cancel = MagicMock()
    on_close = MagicMock()
    el = ConfirmationDialog(is_open, on_ok=on_ok, on_cancel=on_cancel, on_close=on_close, content="Hello")
    _, rc = solara.render(el, handle_error=False)
    dialog = rc.find(vw.Dialog)[0].widget
    assert dialog.v_model
    dialog.v_model = False  # trigger an external close, like escape or clicking away
    assert not is_open.value  # is dialog closed?
    assert on_ok.call_count == 0  # on_ok action should not have been executed
    assert on_cancel.call_count == 1  # on_cancel action should not have been executed
    assert on_close.call_count == 1  # always triggered


def test_confirmation_dialog_custom_button_no_onclick():
    is_open = solara.reactive(True)
    on_ok = MagicMock()
    my_button = solara.Button(label="Not OK")  # no on_click
    el = ConfirmationDialog(is_open, on_ok=on_ok, ok=my_button, content="Are you sure?")
    _, rc = solara.render(el, handle_error=False)
    buttons = rc.find(vw.Btn)
    assert len(buttons) == 2
    assert buttons[0].widget.children == ["Cancel"]
    assert buttons[1].widget.children == ["Not OK"]
    buttons[1].widget.click()
    assert on_ok.call_count == 1  # should still be called


def test_confirmation_dialog_custom_button_with_onclick():
    is_open = solara.reactive(True)
    values = []

    def on_ok():
        values.append("on_ok")

    def on_cancel():
        values.append("on_cancel")

    def on_click_ok():
        values.append("on_click_ok")

    def on_click_cancel():
        values.append("on_click_cancel")

    ok = solara.Button(label="Not OK", on_click=on_click_ok)
    cancel = solara.Button(label="Not Cancel", on_click=on_click_cancel)
    el = ConfirmationDialog(is_open, on_ok=on_ok, on_cancel=on_cancel, ok=ok, cancel=cancel, content="Are you sure?")
    _, rc = solara.render(el, handle_error=False)
    buttons = rc.find(vw.Btn)
    assert len(buttons) == 2
    assert buttons[1].widget.children == ["Not OK"]
    assert buttons[0].widget.children == ["Not Cancel"]
    buttons[1].widget.click()
    assert values == ["on_click_ok", "on_ok"]  # assert on_ok and on_click were both called, in that order
    values.clear()
    # now the same for cancel
    buttons[0].widget.click()
    assert values == ["on_click_cancel", "on_cancel"]
