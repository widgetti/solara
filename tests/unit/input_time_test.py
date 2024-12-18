import datetime as dt
from typing import Optional
from unittest.mock import MagicMock
import ipyvuetify as vw
import solara
from solara.lab.components.input_time import InputTime

now = dt.time(14, 30)
later = dt.time(16, 45)


def test_input_time_typing():
    def on_value(value: dt.time):
        pass

    InputTime(value=now, label="label", on_value=on_value)

    def on_value2(value: Optional[dt.time]):
        pass

    InputTime(value=now, label="label", on_value=on_value2)


def test_input_time():
    on_value = MagicMock()
    on_v_model = MagicMock()
    el = InputTime(value=now, label="label", on_value=on_value)
    box, rc = solara.render(el, handle_error=False)
    input = rc.find(vw.TextField)
    input.widget.observe(on_v_model, "v_model")

    input.widget.v_model = later.strftime("%H:%M")
    assert on_value.call_count == 1
    assert on_v_model.call_count == 1
    on_v_model.reset_mock()
    assert on_value.call_args[0][0] == later

    input.widget.v_model = ""
    assert on_value.call_count == 1
    assert on_v_model.call_count == 1
    assert on_value.call_args[0][0] == later
    assert input.widget.error
    assert input.widget.label == "label (Time cannot be empty)"

    input.widget.v_model = "10:17"
    assert on_value.call_count == 2
    assert on_v_model.call_count == 2
    assert on_value.call_args[0][0] == dt.time(10, 17)
    assert not input.widget.error
    assert input.widget.v_model == dt.time(10, 17).strftime("%H:%M")


def test_input_time_optional():
    on_value = MagicMock()
    on_v_model = MagicMock()
    el = InputTime(value=now, label="label", on_value=on_value, optional=True)
    box, rc = solara.render(el, handle_error=False)
    input = rc.find(vw.TextField)
    input.widget.observe(on_v_model, "v_model")

    input.widget.v_model = later.strftime("%H:%M")
    assert on_value.call_count == 1
    assert on_v_model.call_count == 1
    assert on_value.call_args[0][0] == later

    input.widget.v_model = ""
    assert on_value.call_count == 2
    assert on_v_model.call_count == 2
    assert on_value.call_args[0][0] is None
    assert not input.widget.error

    input.widget.v_model = "10:17"
    assert on_value.call_count == 3
    assert on_v_model.call_count == 3
    assert on_value.call_args[0][0] == dt.time(10, 17)
    assert not input.widget.error
    assert input.widget.v_model == dt.time(10, 17).strftime("%H:%M")


def test_input_time_incomplete_entry():
    on_value = MagicMock()
    on_v_model = MagicMock()

    @solara.component
    def Test():
        def update_value(value: dt.time):
            on_value(value)
            set_value(value)

        value, set_value = solara.use_state(now)

        InputTime(value=value, on_value=update_value, label="label")

    el = Test()
    box, rc = solara.render(el, handle_error=False)
    input = rc.find(vw.TextField)
    input.widget.observe(on_v_model, "v_model")

    input.widget.v_model = "10"
    assert on_value.call_count == 0
    assert on_v_model.call_count == 1
    assert on_value.call_args is None
    assert input.widget.error
    assert input.widget.v_model == "10"
    assert on_v_model.call_count == 1

    input.widget.v_model = "10:17"
    assert on_value.call_count == 1
    assert on_v_model.call_count == 2
    assert on_value.call_args is not None
    assert on_value.call_args[0][0] == dt.time(10, 17)
    assert not input.widget.error
    assert input.widget.v_model == dt.time(10, 17).strftime("%H:%M")


def test_input_time_invalid_format():
    on_value = MagicMock()
    on_v_model = MagicMock()

    @solara.component
    def Test():
        def update_value(value: dt.time):
            on_value(value)
            set_value(value)

        value, set_value = solara.use_state(now)

        InputTime(value=value, on_value=update_value, label="label", twelve_hour_clock=True)

    el = Test()
    box, rc = solara.render(el, handle_error=False)
    input = rc.find(vw.TextField)
    input.widget.observe(on_v_model, "v_model")

    input.widget.v_model = "1:30 PM"
    assert on_value.call_count == 1
    assert on_v_model.call_count == 1
    assert on_value.call_args is not None
    assert on_value.call_args[0][0] == dt.time(13, 30)
    assert not input.widget.error

    input.widget.v_model = "25:00 PM"
    assert on_value.call_count == 1
    assert on_v_model.call_count == 2  # This is still called to reflect change
    assert on_value.call_args[0][0] == dt.time(13, 30)  # Value remains unchanged due to invalid input
    assert input.widget.error
    assert input.widget.label == "label (Time 25:00 PM does not match format I:M p)"


def test_input_time_on_open_value():
    on_open_value = MagicMock()
    on_value = MagicMock()
    el = InputTime(value=now, label="label", on_value=on_value, on_open_value=on_open_value)
    box, rc = solara.render(el, handle_error=False)
    menu = rc.find(vw.VuetifyTemplate)
    assert menu is not None

    # Simulate opening the time picker
    menu.widget.show_menu = True
    assert on_open_value.call_count == 1
    assert on_open_value.call_args[0][0] is True

    # Simulate closing the time picker
    menu.widget.show_menu = False
    assert on_open_value.call_count == 2
    assert on_open_value.call_args[0][0] is False


def test_input_time_boundary_values():
    on_value = MagicMock()
    on_v_model = MagicMock()
    el = InputTime(value=now, label="label", on_value=on_value)
    box, rc = solara.render(el, handle_error=False)
    input = rc.find(vw.TextField)
    input.widget.observe(on_v_model, "v_model")

    # Test boundary value '00:00'
    input.widget.v_model = "00:00"
    assert on_value.call_count == 1
    assert on_v_model.call_count == 1
    assert on_value.call_args[0][0] == dt.time(0, 0)
    assert not input.widget.error

    # Test boundary value '23:59'
    input.widget.v_model = "23:59"
    assert on_value.call_count == 2
    assert on_v_model.call_count == 2
    assert on_value.call_args[0][0] == dt.time(23, 59)
    assert not input.widget.error

    # Test invalid boundary value '24:00'
    input.widget.v_model = "24:00"
    assert on_value.call_count == 2
    assert on_v_model.call_count == 3  # This is still called to reflect change
    assert on_value.call_args[0][0] == dt.time(23, 59)  # Value remains unchanged due to invalid input
    assert input.widget.error
    assert input.widget.label == "label (Time 24:00 does not match format H:M)"
