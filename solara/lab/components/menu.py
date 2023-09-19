import os
from typing import Dict, List, Optional, Union

import ipyvuetify as v
import ipywidgets
import traitlets

import solara


class MenuWidget(v.VuetifyTemplate):
    template_file = os.path.realpath(os.path.join(os.path.dirname(__file__), "menu.vue"))
    activator_element = traitlets.Union([traitlets.List(), traitlets.Dict(), traitlets.Any()], default_value=[]).tag(
        sync=True, **ipywidgets.widget_serialization
    )
    children = traitlets.List(default_value=[]).tag(sync=True, **ipywidgets.widget_serialization)
    show_menu = traitlets.Bool(default_value=False).tag(sync=True)
    style_ = traitlets.Unicode(None, allow_none=True).tag(sync=True)
    context = traitlets.Bool(default_value=False).tag(sync=True)
    use_absolute = traitlets.Bool(default_value=True).tag(sync=True)


@solara.component
def ClickMenu(
    activator: Union[solara.Element, List[solara.Element]],
    children: List[solara.Element] = [],
    style: Optional[Union[str, Dict[str, str]]] = None,
):
    """
    A pop-up menu activated by clicking on an element. `ClickMenu` appears at the cursor position.

    ```solara
    import solara


    @solara.component
    def Page():
        image_url = "/static/public/beach.jpeg"
        image = solara.Image(image=image_url)

        with solara.lab.ClickMenu(
            activator=image,
            style="row-gap: 0;",
        ):
            with solara.Column():
                [solara.Button(f"Click me {i}!", text=True) for i in range(5)]

    ```


    ## Arguments

    * activator: Clicking on this element will open the menu. Accepts either a `solara.Element`, or a list of elements.
    * menu_contents: List of Elements to be contained in the menu.
    * style: CSS style to apply. Applied directly onto the `v-menu` component.
    """
    show = solara.use_reactive(False)
    style_flat = solara.util._flatten_style(style)

    if not isinstance(activator, list):
        activator = [activator]

    return MenuWidget.element(activator_element=activator, children=children, show_menu=show.value, style_=style_flat)


@solara.component
def ContextMenu(
    activator: Union[solara.Element, List[solara.Element]],
    children: List[solara.Element] = [],
    style: Optional[Union[str, Dict[str, str]]] = None,
):
    """
    Opens a context menu when the contextmenu event is triggered on the element `activator`.
    `ContextMenu` also renders the activator element, so rendering it is not necessary separately.

    ```solara
    import solara


    @solara.component
    def Page():
        image_url = "/static/public/beach.jpeg"
        image = solara.Image(image=image_url)

        with solara.lab.ContextMenu(
            activator=image,
            style="row-gap: 0;",
        ):
            with solara.Column():
                [solara.Button(f"Click me {i}!", text=True) for i in range(5)]

    ```

    ## Arguments

    * activator: Clicking on this element will open the menu. Accepts either a `solara.Element`, or a list of elements.
    * children: List of Elements to be contained in the menu
    * style: CSS style to apply. Applied directly onto the `v-menu` component.
    """
    show = solara.use_reactive(False)
    style_flat = solara.util._flatten_style(style)

    if not isinstance(activator, list):
        activator = [activator]

    return MenuWidget.element(activator_element=activator, children=children, show_menu=show.value, style_=style_flat, context=True)


@solara.component
def Menu(
    activator: Union[solara.Element, List[solara.Element]],
    children: List[solara.Element] = [],
    style: Optional[Union[str, Dict[str, str]]] = None,
):
    """
    Opens a menu when the `activator` element is clicked. Is attached to the bottom of the `activator` component.

    ```solara
    import solara


    @solara.component
    def Page():
        btn = solara.Button("Show suboptions")

        with solara.lab.Menu(
            activator=btn,
            style="row-gap: 0;",
        ):
            with solara.Column():
                [solara.Button(f"Click me {str(i)}!", text=True) for i in range(5)]

    ```

    ## Arguments

    * activator: Clicking on this element will open the menu. Accepts either a `solara.Element`, or a list of elements.
    * children: List of Elements to be contained in the menu
    * style: CSS style to apply. Applied directly onto the `v-menu` component.
    """
    show = solara.use_reactive(False)
    style_flat = solara.util._flatten_style(style)

    if not isinstance(activator, list):
        activator = [activator]

    return MenuWidget.element(activator_element=activator, children=children, show_menu=show.value, style_=style_flat, use_absolute=False)
