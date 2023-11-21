from unittest.mock import MagicMock

import ipyvuetify as vw

import solara


def test_chatinput():
    send_callback = MagicMock()
    el = solara.lab.ChatInput(send_callback=send_callback)
    box, rc = solara.render(el, handle_error=False)
    input = rc.find(vw.TextField)
    button = rc.find(vw.Btn)

    input.widget.v_model = "hello"
    assert send_callback.call_count == 0
    input.widget.fire_event("keyup.enter")
    assert send_callback.call_count == 1
    assert send_callback.call_args[0][0] == "hello"
    assert input.widget.v_model == ""
    input.widget.v_model = "hello"
    assert send_callback.call_count == 1
    button.widget.fire_event("click")
    assert send_callback.call_count == 2
    assert send_callback.call_args[0][0] == "hello"
    assert input.widget.v_model == ""
