import os
from datetime import date, datetime, timedelta
from typing import Callable, List, TypeVar

import ipyvue
import traitlets

from solara.kitchensink import react, v

T = TypeVar("T")


@react.component
def FloatSlider(label: str, value: float = 0, min: float = 0, max: float = 0, step: float = 0.1, on_value: Callable[[float], None] = None, thumb_label=True):
    def set_value_cast(value):
        if on_value is None:
            return
        on_value(float(value))

    return v.Slider(v_model=value, on_v_model=set_value_cast, label=label, min=min, max=max, step=step, thumb_label=thumb_label, dense=False, hide_details=True)


@react.component
def IntSlider(label: str, value: int = 0, min: int = 0, max: int = 0, step: int = 1, on_value: Callable[[int], None] = None, thumb_label=True):
    def set_value_cast(value):
        if on_value is None:
            return
        on_value(int(value))

    return v.Slider(v_model=value, on_v_model=set_value_cast, label=label, min=min, max=max, step=step, thumb_label=thumb_label, dense=False, hide_details=True)


@react.component
def ValueSlider(label: str, value: T, values: List[T], on_value: Callable[[T], None] = None):
    index, set_index = react.use_state(values.index(value), key="index")

    def on_index(index):
        set_index(index)
        value = values[index]
        print(index, value)
        if on_value:
            on_value(value)

    return v.Slider(
        v_model=index,
        on_v_model=on_index,
        ticks=True,
        tick_labels=values,
        label=label,
        min=0,
        max=len(values) - 1,
        dense=False,
        hide_details=True,
    )


class DateSliderWidget(ipyvue.VueTemplate):
    template_file = os.path.realpath(os.path.join(os.path.dirname(__file__), "slider_date.vue"))

    min = traitlets.CFloat(0).tag(sync=True)
    days = traitlets.CFloat(0).tag(sync=True)
    value = traitlets.Any(0).tag(sync=True)

    label = traitlets.Unicode("").tag(sync=True)


@react.component
def DateSlider(
    label: str, value: date = date(1981, 7, 28), min: date = date(1950, 1, 1), max: date = date(3000, 12, 30), on_value: Callable[[date], None] = None
):
    def format(d: date):
        return float(datetime(d.year, d.month, d.day).timestamp())

    dt_min = format(min)
    delta: timedelta = max - min
    days = delta.days

    delta_value: timedelta = value - min
    days_value = delta_value.days
    if days_value < 0:
        days_value = 0

    def set_value_cast(value):
        date = min + timedelta(days=value)
        if on_value:
            on_value(date)

    return DateSliderWidget.element(label=label, min=dt_min, days=days, on_value=set_value_cast, value=days_value)
