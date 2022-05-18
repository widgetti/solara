from typing import Callable, List, TypeVar

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
