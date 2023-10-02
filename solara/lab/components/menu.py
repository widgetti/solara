from typing import Dict, List, Optional, Union

import solara
from solara.components.component_vue import component_vue


@component_vue("menu.vue")
def MenuWidget(
    activator: List[solara.Element],
    children: List[solara.Element] = [],
    show_menu: bool = False,
    style: Optional[str] = None,
    context: bool = False,
    use_absolute: bool = True,
):
    pass


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

    return MenuWidget(activator=activator, children=children, show_menu=show.value, style=style_flat)


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

    return MenuWidget(activator=activator, children=children, show_menu=show.value, style=style_flat, context=True)


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

    return MenuWidget(activator=activator, children=children, show_menu=show.value, style=style_flat, use_absolute=False)
