from typing import Callable, List, TypeVar

import solara
from solara.alias import rv

T = TypeVar("T")


@solara.component
def Select(label: str, value: T, values: List[T], on_value: Callable[[T], None] = None):
    """Select a single value from a list of values.

    ## Arguments

     * `label`: Label to display next to the select.
     * `value`: The currently selected value.
     * `values`: List of values to select from.
     * `on_value`: Callback to call when the value changes.

    """
    return rv.Select(
        v_model=value,
        on_v_model=on_value,
        items=values,
        label=label,
        dense=True,
    )


@solara.component
def SelectMultiple(
    label: str,
    values: List[T],
    all_values: List[T],
    on_value: Callable[[List[T]], None] = None,
):
    """Select multiple values from a list of values.

    ## Arguments

        * `label`: Label to display next to the select.
        * `values`: List of currently selected values.
        * `all_values`: List of all values to select from.
        * `on_value`: Callback to call when the value changes.
    """
    return rv.Select(
        v_model=values,
        on_v_model=on_value,
        items=all_values,
        label=label,
        multiple=True,
        dense=False,
    )
