from typing import Optional
from unittest.mock import MagicMock

import ipyvuetify as vw

import solara


def test_input_int_typing():
    def on_value(value: int):
        pass

    solara.InputInt("label", 42, optional=False, on_value=on_value)

    def on_value2(value: Optional[int]):
        pass

    solara.InputInt("label", 42, optional=True, on_value=on_value2)


def test_input_int_optional():
    on_value = MagicMock()
    el = solara.InputInt("label", 42, optional=True, on_value=on_value)
    box, rc = solara.render(el, handle_error=False)
    input = rc.find(vw.TextField)
    input.widget.v_model = "43"
    assert on_value.call_count == 0
    input.widget.fire_event("blur")
    assert on_value.call_count == 1
    assert on_value.call_args[0][0] == 43

    input.widget.v_model = ""
    assert on_value.call_count == 1
    input.widget.fire_event("blur")
    assert on_value.call_count == 2
    assert on_value.call_args[0][0] is None
    rc.close()

    el = solara.InputInt("label", None, optional=True, on_value=on_value)
    box, rc = solara.render(el, handle_error=False)
    input = rc.find(vw.TextField)
    assert input.widget.v_model is None

    rc.render(solara.InputInt("label", 1, optional=True, on_value=on_value))
    assert input.widget.v_model == 1


def test_input_int():
    on_value = MagicMock()
    on_v_model = MagicMock()
    el = solara.InputInt("label", 42, optional=False, on_value=on_value)
    box, rc = solara.render(el, handle_error=False)
    input = rc.find(vw.TextField)
    input.widget.observe(on_v_model, "v_model")

    input.widget.v_model = "43"
    assert on_value.call_count == 0
    assert on_v_model.call_count == 1
    on_v_model.reset_mock()
    input.widget.fire_event("blur")
    assert on_value.call_count == 1
    assert on_value.call_args[0][0] == 43
    assert on_v_model.call_count == 0

    input.widget.v_model = ""
    assert on_value.call_count == 1
    assert on_v_model.call_count == 1
    on_v_model.reset_mock()
    input.widget.fire_event("blur")
    assert on_value.call_count == 1
    assert on_value.call_args[0][0] == 43
    assert input.widget.error
    assert input.widget.label == "label (invalid)"
    assert on_v_model.call_count == 0

    input.widget.v_model = "44"
    assert on_value.call_count == 1
    assert on_v_model.call_count == 1
    input.widget.fire_event("blur")
    assert on_v_model.call_count == 1
    assert on_value.call_count == 2
    assert on_value.call_args[0][0] == 44
    assert not input.widget.error
    assert input.widget.label == "label"


def test_input_int_managed():
    on_value = MagicMock()
    on_v_model = MagicMock()

    @solara.component
    def Test():
        def update_value(value: int):
            on_value(value)
            set_value(value)

        value, set_value = solara.use_state(42)
        solara.InputInt("label", value, optional=False, on_value=update_value)

    el = Test()
    box, rc = solara.render(el, handle_error=False)
    input = rc.find(vw.TextField)
    input.widget.observe(on_v_model, "v_model")

    input.widget.v_model = "1e3"
    assert on_value.call_count == 0
    assert on_v_model.call_count == 1
    input.widget.fire_event("blur")
    assert on_value.call_count == 1
    assert on_value.call_args[0][0] == 1000
    assert not input.widget.error
    assert input.widget.label == "label"
    assert input.widget.v_model == "1e3"
    assert on_v_model.call_count == 1

    input.widget.v_model = "1.1e0"
    assert on_value.call_count == 1
    assert on_v_model.call_count == 2
    input.widget.fire_event("blur")
    assert on_value.call_count == 2
    assert on_v_model.call_count == 3
    assert on_value.call_args[0][0] == 1
    assert not input.widget.error
    assert input.widget.label == "label"
    assert input.widget.v_model == "1"

    input.widget.v_model = "1.1"
    assert on_value.call_count == 2
    assert on_v_model.call_count == 4
    input.widget.fire_event("blur")
    # no change
    assert on_value.call_count == 2
    assert on_v_model.call_count == 5
    assert not input.widget.error
    assert input.widget.label == "label"
    assert input.widget.v_model == "1"


def test_input_float_managed():
    on_value = MagicMock()
    on_v_model = MagicMock()

    @solara.component
    def Test():
        def update_value(value: float):
            on_value(value)
            set_value(value)

        value, set_value = solara.use_state(42.1)
        solara.InputFloat("label", value, optional=False, on_value=update_value)

    el = Test()
    box, rc = solara.render(el, handle_error=False)
    input = rc.find(vw.TextField)
    input.widget.observe(on_v_model, "v_model")

    input.widget.v_model = "1.1e3"
    assert on_value.call_count == 0
    assert on_v_model.call_count == 1
    input.widget.fire_event("blur")
    assert on_value.call_count == 1
    assert on_v_model.call_count == 1
    assert on_value.call_args[0][0] == 1100
    assert not input.widget.error
    assert input.widget.label == "label"
    assert input.widget.v_model == "1.1e3"

    input.widget.v_model = "1,1e3"
    assert on_value.call_count == 1
    assert on_v_model.call_count == 2
    input.widget.fire_event("blur")
    assert on_value.call_count == 1
    assert on_v_model.call_count == 2
    # assert on_value.call_args[0][0] == 1100
    assert not input.widget.error
    assert input.widget.label == "label"
    assert input.widget.v_model == "1,1e3"

    input.widget.v_model = "1.1e0"
    assert on_value.call_count == 1
    assert on_v_model.call_count == 3
    input.widget.fire_event("blur")
    assert on_value.call_count == 2
    assert on_v_model.call_count == 3
    assert on_value.call_args[0][0] == 1.1
    assert not input.widget.error
    assert input.widget.label == "label"
    assert input.widget.v_model == "1.1e0"

    # same value
    input.widget.v_model = "1.1"
    assert on_v_model.call_count == 4
    assert on_value.call_count == 2
    input.widget.fire_event("blur")
    assert on_v_model.call_count == 4
    # no change
    assert on_value.call_count == 2
    assert not input.widget.error
    assert input.widget.label == "label"
    assert input.widget.v_model == "1.1"
