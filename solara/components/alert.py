from typing import Any, Dict, List, Optional, Union

import reacton.ipyvuetify as v

import solara
from solara.util import IPYVUETIFY_V3, _combine_classes


def _alert_variant(outlined: bool, text: bool) -> str:
    if outlined:
        return "outlined"
    if text:
        return "tonal"
    return "elevated"


def _alert_icon_v3(icon: Union[bool, str, None]):
    if isinstance(icon, str):
        return None, [{"name": "prepend", "children": [v.Icon(children=[icon])]}]
    return icon, []


def _alert(
    alert_type: str,
    label: Optional[str],
    icon: Union[bool, str, None],
    dense: bool,
    outlined: bool,
    text: bool,
    children: List[Any],
    classes: List[str],
    kwargs: Dict[str, Any],
):
    if icon is True:
        icon = None
    children = [*([label] if label is not None else []), *children]
    class_ = _combine_classes(classes)
    if IPYVUETIFY_V3:
        icon_v3, v_slots = _alert_icon_v3(icon)
        return v.Alert(
            type=alert_type,
            variant=_alert_variant(outlined, text),
            density="compact" if dense else None,
            icon=icon_v3,
            v_slots=v_slots,
            children=children,
            class_=class_,
            **kwargs,
        )
    return v.Alert(type=alert_type, text=text, outlined=outlined, dense=dense, icon=icon, children=children, class_=class_, **kwargs)


@solara.component
def Success(
    label: Optional[str] = None,
    icon: Union[bool, str, None] = True,
    dense=False,
    outlined=True,
    text=True,
    children=[],
    classes: List[str] = [],
    **kwargs,
):
    """Display a success message (green color).

    ## Arguments

     * `label`: the message to display
     * `icon`: if True, display a check icon, if False, don't display an icon, if a string,
               display the icon with that name ([Overview of available icons](https://pictogrammers.github.io/@mdi/font/4.9.95/)).
     * `dense`: if True, display the message in a dense format, using less vertical height.
     * `outlined`: if True (default), display the message in an outlined border, instead of a filled box.
     * `text`: if True (default), display the message in a text format, which applies a semi-transparent background.
     * `classes`: additional CSS classes to apply.
    """
    return _alert("success", label, icon, dense, outlined, text, children, classes, kwargs)


@solara.component
def Info(
    label: Optional[str] = None,
    icon: Union[bool, str, None] = True,
    dense=False,
    outlined=True,
    text=True,
    children=[],
    classes: List[str] = [],
    **kwargs,
):
    """Display a info message (blue color).

    ## Arguments

     * `label`: the message to display
     * `icon`: if True, display a info icon, if False, don't display an icon, if a string,
               display the icon with that name ([Overview of available icons](https://pictogrammers.github.io/@mdi/font/4.9.95/)).
     * `dense`: if True, display the message in a dense format, using less vertical height.
     * `outlined`: if True (default), display the message in an outlined border, instead of a filled box.
     * `text`: if True (default), display the message in a text format, which applies a semi-transparent background.
     * `classes`: additional CSS classes to apply.
    """
    return _alert("info", label, icon, dense, outlined, text, children, classes, kwargs)


@solara.component
def Warning(
    label: Optional[str] = None,
    icon: Union[bool, str, None] = True,
    dense=False,
    outlined=True,
    text=True,
    children=[],
    classes: List[str] = [],
    **kwargs,
):
    """Display a warning message (orange color).

    ## Arguments

     * `label`: the message to display
     * `icon`: if True, display a exclamation icon, if False, don't display an icon, if a string,
               display the icon with that name ([Overview of available icons](https://pictogrammers.github.io/@mdi/font/4.9.95/)).
     * `dense`: if True, display the message in a dense format, using less vertical height.
     * `outlined`: if True (default), display the message in an outlined border, instead of a filled box.
     * `text`: if True (default), display the message in a text format, which applies a semi-transparent background.
     * `classes`: additional CSS classes to apply.
    """
    return _alert("warning", label, icon, dense, outlined, text, children, classes, kwargs)


@solara.component
def Error(
    label: Optional[str] = None,
    icon: Union[bool, str, None] = True,
    dense=False,
    outlined=True,
    text=True,
    children=[],
    classes: List[str] = [],
    **kwargs,
):
    """Display an error message (red color).

    ## Arguments

     * `label`: the message to display
     * `icon`: if True, display a exclamation in a red triangle icon, if False, don't display an icon, if a string,
               display the icon with that name ([Overview of available icons](https://pictogrammers.github.io/@mdi/font/4.9.95/)).
     * `dense`: if True, display the message in a dense format, using less vertical height.
     * `outlined`: if True (default), display the message in an outlined border, instead of a filled box.
     * `text`: if True (default), display the message in a text format, which applies a semi-transparent background.
     * `classes`: additional CSS classes to apply.
    """
    return _alert("error", label, icon, dense, outlined, text, children, classes, kwargs)
