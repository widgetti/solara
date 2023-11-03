from typing import Callable, Dict, List, Optional, TypeVar, Union, cast, overload

import ipyvuetify as v
import reacton
from typing_extensions import Literal

import solara
from solara.alias import rv
from solara.util import _combine_classes

T = TypeVar("T")


def _get_button_value(button: reacton.core.Element):
    if "value" in button.kwargs:
        value = button.kwargs["value"]
    else:
        value = button.kwargs.get("label")
        if value is None and button.args:
            value = button.args[0]
    return value


@overload
@solara.value_component(None)
def ToggleButtonsSingle(
    value: Union[T, solara.Reactive[T]],
    values: List[T] = ...,
    children: List[reacton.core.Element] = ...,
    on_value: Optional[Callable[[T], None]] = ...,
    dense: bool = ...,
    mandatory: Literal[True] = ...,
    classes: List[str] = ...,
    style: Union[str, Dict[str, str], None] = ...,
) -> reacton.core.ValueElement[v.BtnToggle, T]:
    ...


@overload
@solara.value_component(None)
def ToggleButtonsSingle(
    value: Union[Optional[T], solara.Reactive[Optional[T]]] = None,
    values: List[T] = ...,
    children: List[reacton.core.Element] = ...,
    on_value: Optional[Callable[[Optional[T]], None]] = ...,
    dense: bool = ...,
    mandatory: Literal[False] = ...,
    classes: List[str] = ...,
    style: Union[str, Dict[str, str], None] = ...,
) -> reacton.core.ValueElement[v.BtnToggle, T]:
    ...


@solara.value_component(None)
def ToggleButtonsSingle(
    value: Union[None, T, Optional[T], solara.Reactive[T], solara.Reactive[Optional[T]]] = None,
    values: List[T] = [],
    children: List[reacton.core.Element] = [],
    on_value: Optional[Callable[[T], None]] = None,
    dense: bool = False,
    mandatory: bool = True,
    classes: List[str] = [],
    style: Union[str, Dict[str, str], None] = None,
) -> reacton.core.ValueElement[v.BtnToggle, T]:
    """ToggleButtons for selecting a single value.

    ```solara
    import solara

    foods = ["Kiwi", "Banana", "Apple"]
    food = solara.reactive("Banana")


    @solara.component
    def Page():
        with solara.Card("My favorite food"):
            solara.ToggleButtonsSingle(value=food, values=foods)
            solara.Markdown(f"**Selected**: {food.value}")
    ```

    ### Using Buttons

    Instead of passing the values as a list, we can also use the buttons as children.
    This allows us to customize the buttons, for example to add an icon.

    ```solara
    import solara

    direction = solara.reactive("left")


    @solara.component
    def Page():
        with solara.Card("Pick a direction"):
            # instead of using the values argument, we can use the buttons as children
            # the label of the button will be used as value, if no value is given.
            with solara.ToggleButtonsSingle(value=direction):
                # note that the label and the value are different
                solara.Button("Up", icon_name="mdi-arrow-up-bold", value="up", text=True)
                solara.Button("Down", icon_name="mdi-arrow-down-bold", value="down", text=True)
                solara.Button("Left", icon_name="mdi-arrow-left-bold", value="left", text=True)
                solara.Button("Right", icon_name="mdi-arrow-right-bold", value="right", text=True)
            solara.Markdown(f"**Selected**: {direction.value}")
    ```

    ## Arguments

     * `value`: The currently selected value.
     * `values`: List of values to select from.
     * `children`: List of buttons to use as values.
     * `on_value`: Callback to call when the value changes.
     * `dense`: Whether to use a dense (smaller) style.
     * `mandatory`: Whether a choice is mandatory.
     * `style`: CSS style to apply to the top level element.
     * `classes`: List of CSS classes to be applied to the top level element.
    """
    class_ = _combine_classes(classes)
    style_flat = solara.util._flatten_style(style)
    # TODO: make type safe
    # typing is ignored below due to an issue with the typing; The combination of value being T and on_value being of type Callback[[Optional[T]], None] is
    # not allowed to be passed to use_reactive. We also do not allow this by using our overloads, but this information seems lost at this point by
    # the typechecker
    reactive_value = solara.use_reactive(value, on_value)  # type: ignore
    children = [solara.Button(label=str(value)) for value in values] + children
    values = values + [_get_button_value(button) for button in children]  # type: ignore
    # When mandatory = True, index should not be None, but we are letting the front-end take care of setting index to 0 because of a bug
    # (see https://github.com/widgetti/solara/issues/282)
    # TODO: set index to 0 on python side (after #282 is resolved)
    index, set_index = solara.use_state_or_update(values.index(reactive_value.value) if reactive_value.value in values else None, key="index")

    def on_index(index):
        set_index(index)
        if mandatory:
            value = values[index]
        else:
            value = values[index] if index is not None else None
        reactive_value.set(value)

    return cast(
        reacton.core.ValueElement[v.BtnToggle, T],
        rv.BtnToggle(children=children, multiple=False, mandatory=mandatory, v_model=index, on_v_model=on_index, dense=dense, class_=class_, style_=style_flat),
    )


@solara.value_component(None)
def ToggleButtonsMultiple(
    value: Union[List[T], solara.Reactive[List[T]]] = [],
    values: List[T] = [],
    children: List[reacton.core.Element] = [],
    on_value: Union[Callable[[List[T]], None], None] = None,
    dense: bool = False,
    mandatory: bool = False,
    classes: List[str] = [],
    style: Union[str, Dict[str, str], None] = None,
) -> reacton.core.ValueElement[v.BtnToggle, List[T]]:
    """ToggleButtons for selecting multiple values.

    ### Basic example:
    ```solara
    import solara

    all_languages = "Python C++ Java JavaScript TypeScript BASIC".split()
    languages = solara.reactive([all_languages[0]])


    @solara.component
    def Page():
        with solara.Card("My favorite programming languages"):
            solara.ToggleButtonsMultiple(languages, all_languages)
            solara.Markdown(f"**Selected**: {languages.value}")
    ```

    ## Arguments

     * `value`: The currently selected values.
     * `values`: List of values to select from.
     * `children`: List of buttons to use as values.
     * `on_value`: Callback to call when the value changes.
     * `dense`: Whether to use a dense (smaller) style.
     * `mandatory`: Whether selecting at least one element is mandatory.
     * `style`: CSS style to apply to the top level element.
     * `classes`: List of CSS classes to be applied to the top level element.
    """
    class_ = _combine_classes(classes)
    style_flat = solara.util._flatten_style(style)
    # See comment regarding typing issue in ToggleButtonsSingle
    reactive_value = solara.use_reactive(value, on_value)  # type: ignore
    children = [solara.Button(label=str(value)) for value in values] + children
    allvalues = values + [_get_button_value(button) for button in children]
    indices, set_indices = solara.use_state_or_update([allvalues.index(k) for k in reactive_value.value], key="index")

    def on_indices(indices):
        set_indices(indices)
        value = [allvalues[k] for k in indices]
        reactive_value.set(value)

    return cast(
        reacton.core.ValueElement[v.BtnToggle, List[T]],
        rv.BtnToggle(
            children=children, multiple=True, mandatory=mandatory, v_model=indices, on_v_model=on_indices, dense=dense, class_=class_, style_=style_flat
        ),
    )
