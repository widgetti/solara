from typing import Callable, Dict, List, Optional, Union

from reacton import ipyvue
from reacton import ipyvuetify as v

import solara
import solara.util


@solara.component
def Button(
    label: str = None,
    on_click: Callable[[], None] = None,
    icon_name: str = None,
    children: list = [],
    disabled=False,
    text=False,
    outlined=False,
    color: Optional[str] = None,
    click_event="click",
    classes: List[str] = [],
    style: Union[str, Dict[str, str], None] = None,
    value=None,
    **kwargs,
):
    """A button that can be clicked to trigger an event.

    ## Example

    ```solara
    import solara


    @solara.component
    def Page():
        with solara.Row():
            solara.Button(label="Default")
            solara.Button(label="Default+color", color="primary")
            solara.Button(label="Text", text=True)
            solara.Button(label="Outlined", outlined=True)
            solara.Button(label="Outlined+color", outlined=True, color="primary")
    ```


    ## Arguments

    - `label`: The text to display on the button.
    - `on_click`: A callback function that is called when the button is clicked.
    - `icon_name`: The name of the icon to display on the button ([Overview of available icons](https://pictogrammers.github.io/@mdi/font/4.9.95/)).
    - `children`: A list of child elements to display on the button.
    - `disabled`: Whether the button is disabled.
    - `text`: Whether the button should be displayed as text, it has no shadow and no background.
    - `outlined`: Whether the button should be displayed as outlined, it has no background.
    - `value`: (Optional) When used as a child of a ToggleButtons component, the value of the selected button, see [ToggleButtons](/api/togglebuttons).
    - `classes`: Additional CSS classes to apply.
    - `style`: CSS style to apply.

    ### Deprecated arguments
    - click_event: (Deprecated/export option: The event that triggers the on_click callback, which can include vue event modifiers).

    """
    if label:
        children = [label] + children
    if icon_name:
        children = [v.Icon(left=bool(label), children=[icon_name])] + children
    if "class_" in kwargs:
        kwargs = kwargs.copy()
        class_ = solara.util._combine_classes([*classes, kwargs.pop("class_")])
    else:
        class_ = solara.util._combine_classes(classes)
    kwargs = kwargs.copy()
    style_flat = solara.util._flatten_style(style)
    if "style_" in kwargs:
        style_flat += kwargs.pop("style_")
    if solara.util.ipyvuetify_major_version == 3:
        variant = "elevated"
        if text:
            variant = "text"
        elif outlined:
            variant = "outlined"
        btn = solara.v.Btn(children=children, **kwargs, disabled=disabled, class_=class_, style_=style_flat, color=color, variant=variant)
    else:
        btn = solara.v.Btn(children=children, **kwargs, disabled=disabled, text=text, class_=class_, style_=style_flat, outlined=outlined, color=color)
    ipyvue.use_event(btn, click_event, lambda *_ignore: on_click and on_click())
    return btn
