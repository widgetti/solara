import math
import os
from datetime import date, datetime, timedelta
from typing import Callable, List, Optional, Tuple, TypeVar, Union, cast

import ipyvue
import ipyvuetify
import reacton.core
import traitlets
from typing_extensions import Literal

import solara
from solara.alias import rv

T = TypeVar("T")


@solara.value_component(int)
def SliderInt(
    label: str,
    value: Union[int, solara.Reactive[int]] = 0,
    min: int = 0,
    max: int = 10,
    step: int = 1,
    on_value: Optional[Callable[[int], None]] = None,
    thumb_label: Union[bool, Literal["always"]] = True,
    tick_labels: Union[List[str], Literal["end_points"], bool] = False,
    disabled: bool = False,
):
    """Slider for controlling an integer value.

    ### Basic example:

    ```solara
    import solara

    int_value = solara.reactive(42)


    @solara.component
    def Page():
        solara.SliderInt("Some integer", value=int_value, min=-10, max=120)
        solara.Markdown(f"**Int value**: {int_value.value}")
        with solara.Row():
            solara.Button("Reset", on_click=lambda: int_value.set(42))
    ```


    ## Arguments

    * `label`: Label to display next to the slider.
    * `value`: The currently selected value.
    * `min`: Minimum value.
    * `max`: Maximum value.
    * `step`: Step size.
    * `on_value`: Callback to call when the value changes.
    * `thumb_label`: Show a thumb label when sliding (True), always ("always"), or never (False).
    * `tick_labels`: Show tick labels corresponding to the values (True),
            custom tick labels by passing a list of strings, only end_points ("end_points"),
            or no labels at all (False, the default).
    * `disabled`: Whether the slider is disabled.
    """
    reactive_value = solara.use_reactive(value, on_value)
    del value, on_value

    def set_value_cast(value):
        reactive_value.value = int(value)

    updated_tick_labels = _produce_tick_labels(tick_labels, min, max, step)

    return rv.Slider(
        v_model=reactive_value.value,
        on_v_model=set_value_cast,
        label=label,
        min=min,
        max=max,
        step=step,
        thumb_label=thumb_label,
        tick_labels=updated_tick_labels,
        dense=False,
        hide_details=True,
        disabled=disabled,
    )


@solara.value_component(None)
def SliderRangeInt(
    label: str,
    value: Union[Tuple[int, int], solara.Reactive[Tuple[int, int]]] = (1, 3),
    min: int = 0,
    max: int = 10,
    step: int = 1,
    on_value: Callable[[Tuple[int, int]], None] = None,
    thumb_label: Union[bool, Literal["always"]] = True,
    tick_labels: Union[List[str], Literal["end_points"], bool] = False,
    disabled: bool = False,
) -> reacton.core.ValueElement[ipyvuetify.RangeSlider, Tuple[int, int]]:
    """Slider for controlling a range of integer values.

    ### Basic example:

    ```solara
    import solara

    int_range = solara.reactive((0, 42))


    @solara.component
    def Page():
        solara.SliderRangeInt("Some integer range", value=int_range, min=-10, max=120)
        solara.Markdown(f"**Int range value**: {int_range.value}")
        with solara.Row():
            solara.Button("Reset", on_click=lambda: int_range.set((0, 42)))
    ```

    ## Arguments
    * `label`: Label to display next to the slider.
    * `value`: The currently selected value.
    * `min`: Minimum value.
    * `max`: Maximum value.
    * `step`: Step size.
    * `on_value`: Callback to call when the value changes.
    * `thumb_label`: Show a thumb label when sliding (True), always ("always"), or never (False).
    * `tick_labels`: Show tick labels corresponding to the values (True),
            custom tick labels by passing a list of strings, only end_points ("end_points"),
            or no labels at all (False, the default).
    * `disabled`: Whether the slider is disabled.
    """
    reactive_value = solara.use_reactive(value, on_value)
    del value, on_value

    def set_value_cast(value):
        v1, v2 = value
        reactive_value.set((int(v1), int(v2)))

    updated_tick_labels = _produce_tick_labels(tick_labels, min, max, step)

    return cast(
        reacton.core.ValueElement[ipyvuetify.RangeSlider, Tuple[int, int]],
        rv.RangeSlider(
            v_model=reactive_value.value,
            on_v_model=set_value_cast,
            label=label,
            min=min,
            max=max,
            step=step,
            thumb_label=thumb_label,
            tick_labels=updated_tick_labels,
            dense=False,
            hide_details=True,
            disabled=disabled,
        ),
    )


@solara.value_component(float)
def SliderFloat(
    label: str,
    value: Union[float, solara.Reactive[float]] = 0,
    min: float = 0,
    max: float = 10.0,
    step: float = 0.1,
    on_value: Callable[[float], None] = None,
    thumb_label: Union[bool, Literal["always"]] = True,
    tick_labels: Union[List[str], Literal["end_points"], bool] = False,
    disabled: bool = False,
):
    """Slider for controlling a float value.

    ### Basic example:

    ```solara
    import solara

    float_value = solara.reactive(42.4)


    @solara.component
    def Page():
        solara.SliderFloat("Some integer", value=float_value, min=-10, max=120)
        solara.Markdown(f"**Float value**: {float_value.value}")
        with solara.Row():
            solara.Button("Reset", on_click=lambda: float_value.set(42.5))
    ```

    ## Arguments
    * `label`: Label to display next to the slider.
    * `value`: The current value.
    * `min`: The minimum value.
    * `max`: The maximum value.
    * `step`: The step size.
    * `on_value`: Callback to call when the value changes.
    * `thumb_label`: Show a thumb label when sliding (True), always ("always"), or never (False).
    * `tick_labels`: Show tick labels corresponding to the values (True),
            custom tick labels by passing a list of strings, only end_points ("end_points"),
            or no labels at all (False, the default).
    * `disabled`: Whether the slider is disabled.
    """
    reactive_value = solara.use_reactive(value, on_value)
    del value, on_value

    def set_value_cast(value):
        reactive_value.set(float(value))

    updated_tick_labels = _produce_tick_labels(tick_labels, min, max, step)

    return rv.Slider(
        v_model=reactive_value.value,
        on_v_model=set_value_cast,
        label=label,
        min=min,
        max=max,
        step=step,
        thumb_label=thumb_label,
        tick_labels=updated_tick_labels,
        dense=False,
        hide_details=True,
        disabled=disabled,
    )


@solara.value_component(None)
def SliderRangeFloat(
    label: str,
    value: Union[Tuple[float, float], solara.Reactive[Tuple[float, float]]] = (1.0, 3.0),
    min: float = 0.0,
    max: float = 10.0,
    step: float = 0.1,
    on_value: Callable[[Tuple[float, float]], None] = None,
    thumb_label: Union[bool, Literal["always"]] = True,
    tick_labels: Union[List[str], Literal["end_points"], bool] = False,
    disabled: bool = False,
) -> reacton.core.ValueElement[ipyvuetify.RangeSlider, Tuple[float, float]]:
    """Slider for controlling a range of float values.

    ### Basic example:

    ```solara
    import solara

    float_range = solara.reactive((0.1, 42.4))


    @solara.component
    def Page():
        solara.SliderRangeFloat("Some float range", value=float_range, min=-10, max=120)
        solara.Markdown(f"**Float range value**: {float_range.value}")
        with solara.Row():
            solara.Button("Reset", on_click=lambda: float_range.set((0.1, 42.4)))
    ```

    ## Arguments
    * `label`: Label to display next to the slider.
    * `value`: The current value.
    * `min`: The minimum value.
    * `max`: The maximum value.
    * `step`: The step size.
    * `on_value`: Callback to call when the value changes.
    * `thumb_label`: Show a thumb label when sliding (True), always ("always"), or never (False).
    * `tick_labels`: Show tick labels corresponding to the values (True),
            custom tick labels by passing a list of strings, only end_points ("end_points"),
            or no labels at all (False, the default).
    * `disabled`: Whether the slider is disabled.
    """
    reactive_value = solara.use_reactive(value, on_value)
    del value, on_value

    def set_value_cast(value):
        v1, v2 = value
        reactive_value.set((float(v1), float(v2)))

    updated_tick_labels = _produce_tick_labels(tick_labels, min, max, step)

    return cast(
        reacton.core.ValueElement[ipyvuetify.RangeSlider, Tuple[float, float]],
        rv.RangeSlider(
            v_model=reactive_value.value,
            on_v_model=set_value_cast,
            label=label,
            min=min,
            max=max,
            step=step,
            thumb_label=thumb_label,
            tick_labels=updated_tick_labels,
            dense=False,
            hide_details=True,
            disabled=disabled,
        ),
    )


@solara.value_component(None)
def SliderValue(
    label: str,
    value: Union[T, solara.Reactive[T]],
    values: List[T],
    on_value: Callable[[T], None] = None,
    disabled: bool = False,
) -> reacton.core.ValueElement[ipyvuetify.Slider, T]:
    """Slider for selecting a value from a list of values.

    ### Basic example:

    ```solara
    import solara

    foods = ["Kiwi", "Banana", "Apple"]
    food = solara.reactive("Banana")


    @solara.component
    def Page():
        solara.SliderValue(label="Food", value=food, values=foods)
        solara.Markdown(f"**Selected**: {food.value}")
    ```

    ## Arguments
    * `label`: Label to display next to the slider.
    * `value`: The currently selected value.
    * `values`: List of values to select from.
    * `on_value`: Callback to call when the value changes.
    * `disabled`: Whether the slider is disabled.

    """
    reactive_value = solara.use_reactive(value, on_value)
    del value, on_value
    index, set_index = solara.use_state(values.index(reactive_value.value), key="index")

    def on_index(index):
        set_index(index)
        value = values[index]
        reactive_value.set(value)

    return cast(
        reacton.core.ValueElement[ipyvuetify.Slider, T],
        rv.Slider(
            v_model=index,
            on_v_model=on_index,
            ticks=True,
            tick_labels=values,
            label=label,
            min=0,
            max=len(values) - 1,
            dense=False,
            hide_details=True,
            disabled=disabled,
        ),
    )


class DateSliderWidget(ipyvue.VueTemplate):
    template_file = os.path.realpath(os.path.join(os.path.dirname(__file__), "slider_date.vue"))

    min = traitlets.CFloat(0).tag(sync=True)
    days = traitlets.CFloat(0).tag(sync=True)
    value = traitlets.Any(0).tag(sync=True)

    label = traitlets.Unicode("").tag(sync=True)
    disabled = traitlets.Bool(False).tag(sync=True)


@solara.value_component(date)
def SliderDate(
    label: str,
    value: Union[date, solara.Reactive[date]] = date(2010, 7, 28),
    min: date = date(1981, 1, 1),
    max: date = date(2050, 12, 30),
    on_value: Callable[[date], None] = None,
    disabled: bool = False,
):
    """Slider for controlling a date value.

    ### Basic example:

    ```solara
    import solara
    import datetime

    date_value = solara.reactive(datetime.date(2010, 7, 28))


    @solara.component
    def Page():
        solara.SliderDate("Some date", value=date_value)
        solara.Markdown(f"**Date value**: {date_value.value.strftime('%Y-%b-%d')}")
        with solara.Row():
            solara.Button("Reset", on_click=lambda: date_value.set(datetime.date(2010, 7, 28)))
    ```

    ## Arguments
    * `label`: Label to display next to the slider.
    * `value`: The current value.
    * `min`: The minimum value.
    * `max`: The maximum value.
    * `on_value`: Callback to call when the value changes.
    * `disabled`: Whether the slider is disabled.
    """
    reactive_value = solara.use_reactive(value, on_value)
    del value, on_value

    def format(d: date):
        return float(datetime(d.year, d.month, d.day).timestamp())

    dt_min = format(min)
    delta: timedelta = max - min
    days = delta.days

    delta_value: timedelta = reactive_value.value - min
    days_value = delta_value.days
    if days_value < 0:
        days_value = 0

    def set_value_cast(value):
        date = min + timedelta(days=value)
        reactive_value.set(date)

    return DateSliderWidget.element(label=label, min=dt_min, days=days, on_value=set_value_cast, value=days_value, disabled=disabled)


def _produce_tick_labels(tick_labels: Union[List[str], Literal["end_points"], bool], min: float, max: float, step: float) -> Optional[List[str]]:
    if tick_labels == "end_points":
        num_repeats = int(math.ceil((max - min) / step)) - 1
        _tick_labels = [str(min), *([""] * num_repeats), str(max)]
    elif tick_labels is False:
        _tick_labels = None
    elif tick_labels is True:
        _tick_labels, start = [], min

        while start < max:
            _tick_labels.append(str(start))
            start += step
        _tick_labels.append(str(max))
    else:
        _tick_labels = tick_labels

    return _tick_labels


FloatSlider = SliderFloat
IntSlider = SliderInt
ValueSlider = SliderValue
DateSlider = SliderDate
