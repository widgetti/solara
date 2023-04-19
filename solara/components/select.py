from typing import Callable, List, Optional, TypeVar, Union, cast, overload

import ipyvuetify as v
import reacton.core

import solara
from solara.alias import rv

T = TypeVar("T")


@overload
def Select(
    label: str,
    values: List[T],
    value: None = ...,
    on_value: Optional[Callable[[Optional[T]], None]] = ...,
) -> reacton.core.ValueElement[v.Select, T]:
    ...


@overload
def Select(
    label: str,
    values: List[T],
    value: T = ...,
    on_value: Optional[Callable[[T], None]] = ...,
) -> reacton.core.ValueElement[v.Select, T]:
    ...


@overload
def Select(
    label: str,
    values: List[T],
    value: solara.Reactive[Optional[T]] = ...,
    on_value: Optional[Callable[[Optional[T]], None]] = ...,
) -> reacton.core.ValueElement[v.Select, T]:
    ...


@overload
def Select(
    label: str,
    values: List[T],
    value: solara.Reactive[T] = ...,
    on_value: Optional[Callable[[T], None]] = None,
) -> reacton.core.ValueElement[v.Select, T]:
    ...


@solara.value_component(None)
def Select(
    label: str,
    values: List[T],
    value: Union[None, T, solara.Reactive[T], solara.Reactive[Optional[T]]] = None,
    on_value: Union[None, Callable[[T], None], Callable[[Optional[T]], None]] = None,
) -> reacton.core.ValueElement[v.Select, T]:
    """Select a single value from a list of values.

    ### Basic example:

    ```solara
    import solara

    foods = ["Kiwi", "Banana", "Apple"]
    food = solara.reactive("Banana")


    @solara.component
    def Page():
        solara.Select(label="Food", value=food, values=foods)
        solara.Markdown(f"**Selected**: {food.value}")
    ```

    ## Arguments

     * `label`: Label to display next to the select.
     * `value`: The currently selected value.
     * `values`: List of values to select from.
     * `on_value`: Callback to call when the value changes.

    """
    # next line is very hard to get right with typing
    # might need an overload on use_reactive, when value is None
    reactive_value = solara.use_reactive(value, on_value)  # type: ignore
    del value, on_value
    return cast(
        reacton.core.ValueElement[v.Select, T],
        rv.Select(
            v_model=reactive_value.value,
            on_v_model=reactive_value.set,
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

    ### Basic example:

    ```solara
    import solara

    all_languages = "Python C++ Java JavaScript TypeScript BASIC".split()
    languages = solara.reactive([all_languages[0]])


    @solara.component
    def Page():
        solara.SelectMultiple("Languages", languages, all_languages)
        solara.Markdown(f"**Selected**: {languages.value}")
    ```

    ## Arguments

        * `label`: Label to display next to the select.
        * `values`: List of currently selected values.
        * `all_values`: List of all values to select from.
        * `on_value`: Callback to call when the value changes.
    """
    reactive_values = solara.use_reactive(values, on_value)
    del values, on_value
    return cast(
        reacton.core.ValueElement[v.Select, List[T]],
        rv.Select(
            v_model=reactive_values.value,
            on_v_model=reactive_values.set,
            items=all_values,
            label=label,
            multiple=True,
            dense=False,
        ),
    )
