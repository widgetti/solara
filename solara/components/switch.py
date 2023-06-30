from typing import Callable, Union

import reacton.ipyvuetify as v

import solara


@solara.value_component(bool)
def Switch(
    *,
    label=None,
    value: Union[bool, solara.Reactive[bool]] = True,
    on_value: Callable[[bool], None] = None,
    disabled=False,
    style: str = None,
):
    """A switch component provides users the ability to choose between two distinct values. But aesthetically different
    from a checkbox.

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
     * `style`: A string of CSS styles to apply to the switch.
    """
    reactive_value = solara.use_reactive(value, on_value)
    del value, on_value
    children = []
    if label is not None:
        children = [label]
    return v.Switch(label=label, v_model=reactive_value.value, on_v_model=reactive_value.set, disabled=disabled, style_=style, children=children)
