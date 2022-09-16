from typing import Callable, List, TypeVar

from solara.kitchensink import react, v

T = TypeVar("T")


@react.component
def Select(label: str, value: T, values: List[T], on_value: Callable[[T], None] = None):
    return v.Select(
        v_model=value,
        on_v_model=on_value,
        items=values,
        label=label,
        dense=True,
    )


@react.component
def SelectMultiple(label: str, values: List[T], all_values: List[T], on_value: Callable[[List[T]], None] = None):
    return v.Select(
        v_model=values,
        on_v_model=on_value,
        items=all_values,
        label=label,
        multiple=True,
        dense=False,
    )
