from unittest.mock import MagicMock

import ipyvuetify as vw

import solara


def test_switch():
    on_value = MagicMock()
    el = solara.Switch(label="label", value=True, on_value=on_value)
    _, rc = solara.render(el, handle_error=False)
    switch = rc.find(vw.Switch)
    switch.widget.v_model = False
    assert on_value.call_count == 1
    switch.widget.v_model = False
    assert on_value.call_count == 1
    switch.widget.v_model = True
    assert on_value.call_count == 2
    rc.close()
