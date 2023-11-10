from typing import Callable, Dict, List, Optional, Union

import reacton.ipyvuetify as v

import solara


@solara.value_component(bool)
def Switch(
    *,
    label: str = None,
    value: Union[bool, solara.Reactive[bool]] = True,
    on_value: Callable[[bool], None] = None,
    disabled: bool = False,
    children: list = [],
    classes: List[str] = [],
    style: Optional[Union[str, Dict[str, str]]] = None,
):
    """A switch component provides users the ability to choose between two distinct values. But aesthetically different from a checkbox.

    Basic examples

    ```solara
    import solara

    show_message = solara.reactive(True)
    disable = solara.reactive(False)


    @solara.component
    def Page():
        with solara.Column():
            with solara.Row():
                solara.Switch(label="Hide Message", value=show_message, disabled=disable.value)
                solara.Switch(label="Disable Message Switch", value=disable)

            if show_message.value:
                solara.Markdown("## Use Switch to show/hide message")

    ```


    ## Arguments

     * `label`: The label to display next to the switch.
     * `value`: The current value of the switch (True or False).
     * `on_value`: A callback that is called when the switch is toggled.
     * `disabled`: If True, the switch is disabled and cannot be used.
     * `children`: A list of child elements to display on the switch.
     * `classes`: Additional CSS classes to apply.
     * `style`: CSS style to apply.

    """
    reactive_value = solara.use_reactive(value, on_value)
    del value, on_value

    if label:
        children = [label] + children

    return v.Switch(
        label=label,
        v_model=reactive_value.value,
        on_v_model=reactive_value.set,
        disabled=disabled,
        class_=solara.util._combine_classes(classes),
        style_=solara.util._flatten_style(style),
        children=children,
    )
