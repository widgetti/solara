import datetime as dt
from typing import Optional
from unittest.mock import MagicMock

import ipyvuetify as vw

import solara
from solara.lab import InputDate, InputDateRange

today = dt.date.today()
tomorrow = today + dt.timedelta(days=1)


def test_input_date_typing():
    def on_value(value: dt.date):
        pass

    InputDate(value=today, label="label", on_value=on_value)

    def on_value2(value: Optional[dt.date]):
        pass

    InputDate(value=today, label="label", on_value=on_value2)


def test_input_date():
    on_value = MagicMock()
    on_v_model = MagicMock()
    el = InputDate(value=today, label="label", on_value=on_value)
    box, rc = solara.render(el, handle_error=False)
    input = rc.find(vw.TextField)
    input.widget.observe(on_v_model, "v_model")

    input.widget.v_model = tomorrow.strftime("%Y/%m/%d")
    assert on_value.call_count == 1
    assert on_v_model.call_count == 1
    on_v_model.reset_mock()
    assert on_value.call_args[0][0] == tomorrow

    input.widget.v_model = ""
    assert on_value.call_count == 1
    assert on_v_model.call_count == 1
    assert on_value.call_args[0][0] == tomorrow
    assert input.widget.error
    assert input.widget.label == "label (Date cannot be empty)"

    input.widget.v_model = "2023/10/17"
    assert on_value.call_count == 2
    assert on_v_model.call_count == 2
    assert on_value.call_args[0][0] == dt.date(2023, 10, 17)
    assert not input.widget.error
    assert input.widget.v_model == dt.date(2023, 10, 17).strftime("%Y/%m/%d")


def test_input_date_optional():
    on_value = MagicMock()
    on_v_model = MagicMock()
    el = InputDate(value=today, label="label", on_value=on_value, optional=True)
    box, rc = solara.render(el, handle_error=False)
    input = rc.find(vw.TextField)
    input.widget.observe(on_v_model, "v_model")

    input.widget.v_model = tomorrow.strftime("%Y/%m/%d")
    assert on_value.call_count == 1
    assert on_v_model.call_count == 1
    assert on_value.call_args[0][0] == tomorrow

    input.widget.v_model = ""
    assert on_value.call_count == 2
    assert on_v_model.call_count == 2
    assert on_value.call_args[0][0] is None
    assert not input.widget.error

    input.widget.v_model = "2023/10/17"
    assert on_value.call_count == 3
    assert on_v_model.call_count == 3
    assert on_value.call_args[0][0] == dt.date(2023, 10, 17)
    assert not input.widget.error
    assert input.widget.v_model == dt.date(2023, 10, 17).strftime("%Y/%m/%d")


def test_input_date_incomplete_entry():
    on_value = MagicMock()
    on_v_model = MagicMock()

    @solara.component
    def Test():
        def update_value(value: int):
            on_value(value)
            set_value(value)

        value, set_value = solara.use_state(today)

        InputDate(value=value, on_value=update_value, label="label")

    el = Test()
    box, rc = solara.render(el, handle_error=False)
    input = rc.find(vw.TextField)
    input.widget.observe(on_v_model, "v_model")

    input.widget.v_model = "2023/10"
    assert on_value.call_count == 0
    assert on_v_model.call_count == 1
    assert on_value.call_args is None
    assert input.widget.error
    assert input.widget.v_model == "2023/10"
    assert on_v_model.call_count == 1

    input.widget.v_model = "2023/10/17"
    assert on_value.call_count == 1
    assert on_v_model.call_count == 2
    # Without below assert mypy fails
    assert on_value.call_args is not None
    assert on_value.call_args[0][0] == dt.date(2023, 10, 17)
    assert not input.widget.error
    assert input.widget.v_model == dt.date(2023, 10, 17).strftime("%Y/%m/%d")


def test_input_date_range():
    on_value = MagicMock()
    on_v_model = MagicMock()
    el = InputDateRange(value=tuple([today, tomorrow]), label="label", on_value=on_value)
    box, rc = solara.render(el, handle_error=False)
    text_field = rc.find(vw.TextField)
    input = rc.find(vw.DatePicker)
    text_field.widget.observe(on_v_model, "v_model")

    assert input.widget.v_model == [today.strftime("%Y-%m-%d"), tomorrow.strftime("%Y-%m-%d")]
    input.widget.v_model = [tomorrow.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")]
    assert on_value.call_count == 1
    assert on_v_model.call_count == 1
    on_v_model.reset_mock()
    assert on_value.call_args[0][0] == tuple([tomorrow, today])

    input.widget.v_model = ["2023-10-17", None]
    assert on_value.call_count == 2
    # We enter no date, so on_v_model does not get called
    assert on_v_model.call_count == 1
    assert on_value.call_args[0][0] == tuple([dt.date(2023, 10, 17), None])
    assert text_field.widget.error
    assert text_field.widget.label == "label (Please select two dates)"

    input.widget.v_model = ["2023-10-17", tomorrow.strftime("%Y-%m-%d")]
    assert on_value.call_count == 3
    assert on_v_model.call_count == 2
    assert on_value.call_args[0][0] == tuple([dt.date(2023, 10, 17), tomorrow])
    assert not text_field.widget.error
    assert text_field.widget.v_model == f"{dt.date(2023, 10, 17).strftime('%Y/%m/%d')} - {tomorrow.strftime('%Y/%m/%d')}"
