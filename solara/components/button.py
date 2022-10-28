from typing import Callable

from reacton import ipyvue
from reacton import ipyvuetify as v

import solara


@solara.component
def Button(
    label: str = None,
    on_click: Callable[[], None] = None,
    icon_name: str = None,
    children: list = [],
    disabled=False,
    text=False,
    click_event="click",
    value=None,
    **kwargs,
):
    """A button that can be clicked to trigger an event.


    ## Arguments

    - label: The text to display on the button.
    - on_click: A callback function that is called when the button is clicked.
    - icon_name: The name of the icon to display on the button ([Overview of available icons](https://pictogrammers.github.io/@mdi/font/4.9.95/)).
    - children: A list of child elements to display on the button.
    - disabled: Whether the button is disabled.

    ### Deprecated arguments
    - click_event: (Deprecated/export option: The event that triggers the on_click callback, which can include vue event modifiers).
    - value: (Deprecated: The value to use for ToggleButtons).

    """
    if label:
        children = [label] + children
    if icon_name:
        children = [v.Icon(left=bool(label), children=[icon_name])] + children
    btn = v.Btn(children=children, **kwargs, disabled=disabled, text=text)
    ipyvue.use_event(btn, click_event, lambda *_ignore: on_click and on_click())
    return btn
