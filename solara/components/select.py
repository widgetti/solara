from typing import Callable, List, Optional, TypeVar, cast

import ipyvuetify as v
import reacton.core

import solara
from solara.alias import rv

T = TypeVar("T")


@solara.value_component(None)
def Select(label: str, values: List[T], value: Optional[T] = None, on_value: Callable[[T], None] = None) -> reacton.core.ValueElement[v.Select, T]:
    """Select a single value from a list of values.

    ## Arguments

     * `label`: Label to display next to the select.
     * `value`: The currently selected value.
     * `values`: List of values to select from.
     * `on_value`: Callback to call when the value changes.

    """
    return cast(
        reacton.core.ValueElement[v.Select, T],
        rv.Select(
            v_model=value,
            on_v_model=on_value,
            items=values,
            label=label,
            dense=True,
        ),
    )


@solara.value_component(None)
def SelectMultiple(
    label: str,
    values: List[T],
    all_values: List[T],
    on_value: Callable[[List[T]], None] = None,
) -> reacton.core.ValueElement[v.Select, List[T]]:
    """Select multiple values from a list of values.

    ## Arguments

        * `label`: Label to display next to the select.
        * `values`: List of currently selected values.
        * `all_values`: List of all values to select from.
        * `on_value`: Callback to call when the value changes.
    """
    return cast(
        reacton.core.ValueElement[v.Select, List[T]],
        rv.Select(
            v_model=values,
            on_v_model=on_value,
            items=all_values,
            label=label,
            multiple=True,
            dense=False,
        ),
    )
