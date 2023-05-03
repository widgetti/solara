from unittest.mock import MagicMock

import ipyvuetify as vw

import solara


def test_checkbox():
    on_value = MagicMock()
    el = solara.Checkbox(label="label", value=True, on_value=on_value)
    box, rc = solara.render(el, handle_error=False)
    checkbox = rc.find(vw.Checkbox)
    checkbox.widget.v_model = False
    assert on_value.call_count == 1
    checkbox.widget.v_model = False
    assert on_value.call_count == 1
    rc.close()


def test_checkbox_no_callback_on_managed():
    on_value = MagicMock()
    el = solara.Checkbox(label="label", value=True, on_value=on_value)
    box, rc = solara.render(el, handle_error=False)
    assert on_value.call_count == 0

    # changing the value externally should *not* call the callback
    el2 = solara.Checkbox(label="label", value=False, on_value=on_value)
    rc.render(el2)
    assert on_value.call_count == 0
