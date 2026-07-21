from typing import Callable, Dict, List, Optional, Union

import solara
from solara.components.component_vue import component_vue


@component_vue("menu.vue")
def MenuWidget(
    activator: List[solara.Element],
    show_menu: bool,
    on_show_menu: Optional[Callable] = None,
    close_on_content_click: bool = True,
    children: List[solara.Element] = [],
    style: Optional[str] = None,
    context: bool = False,
    use_absolute: bool = True,
    use_activator_width: bool = True,
):
    pass


@solara.component
def ClickMenu(
    activator: Union[solara.Element, List[solara.Element]],
    open_value: Union[solara.Reactive[bool], bool] = False,
    on_open_value: Optional[Callable] = None,
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
    * open_value: Controls and communicates the state of the menu. If True, the menu is open. If False, the menu is closed.
    * on_open_value: Function to call when the menu is opened or closed.
    * menu_contents: List of Elements to be contained in the menu.
    * style: CSS style to apply. Applied directly onto the `v-menu` component.
    """
    open_reactive = solara.use_reactive(open_value, on_open_value)
    del open_value

    style_flat = solara.util._flatten_style(style)

    if not isinstance(activator, list):
        activator = [activator]

    activator_wrapper = solara.v.Html(tag="div", v_bind="x.props", children=activator)
    return solara.v.Menu(
        v_model=open_reactive.value,
        on_v_model=open_reactive.set,
        v_slots=[{"name": "activator", "variable": "x", "children": activator_wrapper}],
        close_on_content_click=True,
        location="bottom",
        offset=4,
        children=[solara.v.List(children=children, style_="padding: 0;")],
        style_=style_flat,
    )


@solara.component
def ContextMenu(
    activator: Union[solara.Element, List[solara.Element]],
    open_value: Union[solara.Reactive[bool], bool] = False,
    on_open_value: Optional[Callable] = None,
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
    * open_value: Controls and communicates the state of the menu. If True, the menu is open. If False, the menu is closed.
    * on_open_value: Function to call when the menu is opened or closed.
    * children: List of Elements to be contained in the menu
    * style: CSS style to apply. Applied directly onto the `v-menu` component.
    """
    open_reactive = solara.use_reactive(open_value, on_open_value)
    del open_value
    style_flat = solara.util._flatten_style(style)

    if not isinstance(activator, list):
        activator = [activator]

    activator_wrapper = solara.v.Html(tag="div", children=activator)

    def add_context_menu_handler():
        widget = solara.get_widget(activator_wrapper)

        def open_menu(*ignore):
            open_reactive.set(True)

        widget.on_event("contextmenu.prevent", open_menu)

        def cleanup():
            widget.on_event("contextmenu.prevent", open_menu, remove=True)

        return cleanup

    solara.use_effect(add_context_menu_handler, [activator_wrapper])

    return solara.v.Menu(
        v_model=open_reactive.value,
        on_v_model=open_reactive.set,
        v_slots=[{"name": "activator", "variable": "x", "children": activator_wrapper}],
        close_on_content_click=True,
        open_on_click=False,
        location="bottom",
        offset=4,
        children=[solara.v.List(children=children, style_="padding: 0;")],
        style_=style_flat,
    )


@solara.component
def Menu(
    activator: Union[solara.Element, List[solara.Element]],
    open_value: Union[solara.Reactive[bool], bool] = False,
    on_open_value: Optional[Callable] = None,
    close_on_content_click: bool = True,
    children: List[solara.Element] = [],
    style: Optional[Union[str, Dict[str, str]]] = None,
    use_activator_width: bool = True,
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
    * open_value: Controls and communicates the state of the menu. If True, the menu is open. If False, the menu is closed.
    * on_open_value: Function to call when the menu is opened or closed.
    * children: List of Elements to be contained in the menu
    * style: CSS style to apply. Applied directly onto the `v-menu` component.
    * use_activator_width: If True, the menu will have a minimum width equal to the activator element.
      If False, the menu width will be determined by the content.
    """
    open_reactive = solara.use_reactive(open_value, on_open_value)
    del open_value

    style_flat = solara.util._flatten_style(style)

    if not isinstance(activator, list):
        activator = [activator]

    activator_wrapper = solara.v.Html(tag="div", v_bind="x.props", children=activator)
    min_width = None if use_activator_width else "auto"
    return solara.v.Menu(
        v_model=open_reactive.value,
        on_v_model=open_reactive.set,
        v_slots=[{"name": "activator", "variable": "x", "children": activator_wrapper}],
        close_on_content_click=close_on_content_click,
        location="bottom",
        offset=4,
        min_width=min_width,
        children=[solara.v.List(children=children, style_="padding: 0;")],
        style_=style_flat,
    )
