from typing import Callable, List, TypeVar

import reacton

import solara
from solara.alias import rv

T = TypeVar("T")


def _get_button_value(button: reacton.core.Element):
    value = button.kwargs.get("value")
    if value is None:
        value = button.kwargs.get("label")
    if value is None and button.args:
        value = button.args[0]
    return value


@solara.component
def ToggleButtonsSingle(value: T, values: List[T] = [], children: List[reacton.core.Element] = [], on_value: Callable[[T], None] = None):
    """ToggleButtons for selecting a single value.

    ## Arguments

    * `value`: The currently selected value.
    * `values`: List of values to select from.
    * `children`: List of buttons to use as values.
    * `on_value`: Callback to call when the value changes.
    """
    children = [solara.Button(label=str(value)) for value in values] + children
    values = values + [_get_button_value(button) for button in children]
    index, set_index = solara.use_state_or_update(values.index(value), key="index")

    def on_index(index):
        set_index(index)
        value = values[index]
        if on_value:
            on_value(value)

    with rv.BtnToggle(children=children, multiple=False, mandatory=True, v_model=index, on_v_model=on_index) as main:
        pass
    return main


@solara.component
def ToggleButtonsMultiple(value: List[T], values: List[T] = [], children: List[reacton.core.Element] = [], on_value: Callable[[List[T]], None] = None):
    """ToggleButtons for selecting multiple values.

    ## Arguments

    * `value`: The currently selected values.
    * `values`: List of values to select from.
    * `children`: List of buttons to use as values.
    * `on_value`: Callback to call when the value changes.
    """
    children = [solara.Button(label=str(value)) for value in values] + children
    allvalues = values + [_get_button_value(button) for button in children]
    indices, set_indices = solara.use_state_or_update([allvalues.index(k) for k in value], key="index")

    def on_indices(indices):
        set_indices(indices)
        value = [allvalues[k] for k in indices]
        if on_value:
            on_value(value)

    with rv.BtnToggle(children=children, multiple=True, mandatory=False, v_model=indices, on_v_model=on_indices) as main:
        pass
    return main
