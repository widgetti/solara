from typing import Callable, List, TypeVar

from solara.kitchensink import react, v

T = TypeVar("T")


def _get_button_value(button: react.core.Element):
    value = button.kwargs.get("value")
    if value is None:
        value = button.kwargs.get("label")
    if value is None and button.args:
        value = button.args[0]
    return value


@react.component
def ToggleButtonsSingle(value: T, children: List[react.core.Element] = [], on_value: Callable[[T], None] = None):
    values = [_get_button_value(button) for button in children]
    index, set_index = react.use_state(values.index(value), key="index")

    def on_index(index):
        set_index(index)
        value = values[index]
        if on_value:
            on_value(value)

    with v.BtnToggle(children=children, multiple=False, mandatory=True, v_model=index, on_v_model=on_index) as main:
        pass
    return main


@react.component
def ToggleButtonsMultiple(value: List[T], children: List[react.core.Element] = [], on_value: Callable[[List[T]], None] = None):
    allvalues = [_get_button_value(button) for button in children]
    indices, set_indices = react.use_state([allvalues.index(k) for k in value], key="index")

    def on_indices(indices):
        set_indices(indices)
        value = [allvalues[k] for k in indices]
        if on_value:
            on_value(value)

    with v.BtnToggle(children=children, multiple=True, mandatory=False, v_model=indices, on_v_model=on_indices) as main:
        pass
    return main
