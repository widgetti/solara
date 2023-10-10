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
    Show a pop-up menu by clicking on the `activator` element. The menu appears at the cursor position.

    ```solara
    import solara


    @solara.component
    def Page():
        image_url = "/static/public/beach.jpeg"
        image = solara.Image(image=image_url)

        with solara.lab.ClickMenu(activator=image):
            with solara.Column(gap="0px"):
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
    Show a context menu by triggering the contextmenu event on the `activator` element. The menu appears at the cursor position.

    A contextmenu event is typically triggered by clicking the right mouse button, or by pressing the context menu key.

    ```solara
    import solara


    @solara.component
    def Page():
        image_url = "/static/public/beach.jpeg"
        image = solara.Image(image=image_url)

        with solara.lab.ContextMenu(activator=image):
            with solara.Column(gap="0px"):
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
    Show a pop-up menu by clicking on the `activator` element. The menu appears below the `activator` element.

    ```solara
    import solara


    @solara.component
    def Page():
        btn = solara.Button("Show suboptions")

        with solara.lab.Menu(activator=btn):
            with solara.Column(gap="0px"):
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
