from unittest.mock import MagicMock

import ipyvuetify as vw

import solara
from solara.lab.components.confirmation_dialog import ConfirmationDialog


def test_confirmation_dialog_ok():
    is_open = solara.reactive(True)
    on_ok = MagicMock()
    el = ConfirmationDialog(is_open, on_ok=on_ok, content="Hello")
    _, rc = solara.render(el, handle_error=False)
    buttons = rc.find(vw.Btn)
    assert len(buttons) == 2
    buttons[0].widget.click()
    assert on_ok.call_count == 1  # was OK button clicked?
    assert not is_open.value  # is dialog closed?


def test_confirmation_dialog_cancel():
    is_open = solara.reactive(True)
    on_ok = MagicMock()
    el = ConfirmationDialog(is_open, on_ok=on_ok, content="Hello")
    _, rc = solara.render(el, handle_error=False)
    buttons = rc.find(vw.Btn)
    assert len(buttons) == 2
    buttons[1].widget.click()
    assert on_ok.call_count == 0  # on_ok action should not have been executed
    assert not is_open.value  # is dialog closed?


def test_confirmation_dialog_custom_button_no_onclick():
    is_open = solara.reactive(True)
    on_ok = MagicMock()
    my_button = solara.Button(label="Not OK")  # no on_click
    el = ConfirmationDialog(is_open, on_ok=on_ok, ok=my_button, content="Are you sure?")
    _, rc = solara.render(el, handle_error=False)
    buttons = rc.find(vw.Btn)
    assert len(buttons) == 2
    assert buttons[0].widget.children == ["Not OK"]
    assert buttons[1].widget.children == ["Cancel"]
    buttons[0].widget.click()
    assert on_ok.call_count == 1  # should still be called


def test_confirmation_dialog_custom_button_with_onclick():
    is_open = solara.reactive(True)
    values = []

    def on_ok():
        values.append(1)

    def on_click():
        lambda: values.append(2)

    my_button = solara.Button(label="Not OK", on_click=on_click)
    el = ConfirmationDialog(is_open, on_ok=on_ok, ok=my_button, content="Are you sure?")
    _, rc = solara.render(el, handle_error=False)
    buttons = rc.find(vw.Btn)
    assert len(buttons) == 2
    assert buttons[0].widget.children == ["Not OK"]
    assert buttons[1].widget.children == ["Cancel"]
    buttons[0].widget.click()
    assert values == [1, 2]  # assert on_ok and on_click were both called, in that order
