from typing import Callable, List

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
    click_event="click",
    classes: List[str] = [],
    value=None,
    **kwargs,
):
    """A button that can be clicked to trigger an event.


    ## Arguments

    - `label`: The text to display on the button.
    - `on_click`: A callback function that is called when the button is clicked.
    - `icon_name`: The name of the icon to display on the button ([Overview of available icons](https://pictogrammers.github.io/@mdi/font/4.9.95/)).
    - `children`: A list of child elements to display on the button.
    - `disabled`: Whether the button is disabled.
    - `value`: (Optional) When used as a child of a ToggleButtons component, the value of the selected button, see [ToggleButtons](/api/togglebuttons).
    - `classes`: additional CSS classes to apply.

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
    btn = v.Btn(children=children, **kwargs, disabled=disabled, text=text, class_=class_)
    ipyvue.use_event(btn, click_event, lambda *_ignore: on_click and on_click())
    return btn
