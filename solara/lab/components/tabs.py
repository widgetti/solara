from typing import Callable, Dict, List, Optional, TypeVar, Union

import solara
from solara import v


@solara.component
def Tab(
    label: Union[None, str, solara.Element] = None,
    icon_name: Optional[str] = None,
    path_or_route: Union[None, str, "solara.Route"] = None,
    disabled=False,
    classes: List[str] = [],
    style: Union[str, Dict[str, str], None] = None,
    children: List[solara.Element] = [],
    tab_children: List[Union[solara.Element, str]] = [],
):
    """An item in a Tabs component.

    (*Note: [This component is experimental and its API may change in the future](/docs/lab).*)

    Should be a direct child of a [Tabs](/api/tabs).

    ## Arguments
     * `label`: The label of the tab.
     * `icon_name`: The name of the icon to display in the tab.
     * `path_or_route`: The path or route to navigate to when the tab is clicked.
     * `disabled`: Whether the tab is disabled.
     * `classes`: Additional CSS classes to apply.
     * `style`: CSS style to apply.
     * `children`: The children of the tab. These will be displayed when the tab is active.
     * `tab_children`: The children of the tab header. These will be displayed in the tab
        header, if a label or icon_name is provided they are prepended to the `tab_children`.

    """
    if label is not None:
        tab_children = [label] + tab_children
    if icon_name:
        tab_children = [v.Icon(left=bool(label), children=[icon_name])] + tab_children
    style_flat = solara.util._flatten_style(style)
    class_ = solara.util._combine_classes(classes)
    # note: children is not used, it is only used in the Tabs component
    return v.Tab(children=tab_children, disabled=disabled, class_=class_, style_=style_flat)


T = TypeVar("T")


@solara.component
def Tabs(
    value: Union[None, int, "solara.Reactive[int]"] = None,
    on_value: Optional[Callable[[int], None]] = None,
    color: Optional[str] = None,
    background_color: Optional[str] = None,
    slider_color: Optional[str] = None,
    dark: bool = False,
    grow: bool = False,
    vertical=False,
    align: str = "left",
    lazy=False,
    children: List[solara.Element] = [],
):
    """A tabbed container showing one tab at a time.

    (*Note: [This component is experimental and its API may change in the future](/docs/lab).*)

    Note that if Tabs are used as a child of the [AppBar](/api/appbar) component, the tabs
    will be placed under the app bar. See our [authorization app](/apps/authorization) for an example.

    If the children [Tab](/api/tab) elements are passed a `path_or_route` argument, the active tab
    will be based on the path of the current page.


    ## Examples

    ### Only tabs headers

    ```solara
    import solara
    import solara.lab


    @solara.component
    def Page():
        with solara.lab.Tabs():
            solara.lab.Tab("Tab 1")
            solara.lab.Tab("Tab 2")
    ```

    ### Tabs with content

    This is usually only used when the tabs are placed in the [AppBar](/api/appbar) component.

    ```solara
    import solara
    import solara.lab


    @solara.component
    def Page():
        with solara.lab.Tabs():
            with solara.lab.Tab("Tab 1"):
                solara.Markdown("Hello")
            with solara.lab.Tab("Tab 2"):
                solara.Markdown("World")
    ```


    ### Tabs events

    The `value` on the Tabs component is a reactive value that can be used to
    listen to changes in the selected tab and make the UI respond to it.

    ```solara
    import solara
    import solara.lab

    tab_index = solara.reactive(0)


    @solara.component
    def Page():

        def next_tab():
            tab_index.value = (tab_index.value + 1) % 2

        solara.Title(f"Tab {tab_index.value + 1}")
        solara.Button('Next Tab', on_click=next_tab)

        with solara.lab.Tabs(value=tab_index):
            with solara.lab.Tab("Tab 1"):
                solara.Markdown("Hello")
            with solara.lab.Tab("Tab 2"):
                solara.Markdown("World")
            with solara.lab.Tab("Disabled", disabled=True):
                solara.Markdown("World")

    ```

    ### Advanced tabs

    Tabs can be nested, styled and placed vertically.

    ```solara
    import solara
    import solara.lab


    @solara.component
    def Page():
        with solara.lab.Tabs(background_color="primary", dark=True):
            with solara.lab.Tab("Home", icon_name="mdi-home"):
                solara.Markdown("Hello")
            with solara.lab.Tab("Advanced", icon_name="mdi-apps"):
                with solara.lab.Tabs(grow=True, background_color="primary", dark=True, slider_color="green"):
                    with solara.lab.Tab("Settings", icon_name="mdi-cogs"):
                        with solara.lab.Tabs(vertical=True, slider_color="green"):
                            with solara.lab.Tab("User", icon_name="mdi-account"):
                                solara.Markdown("User settings")
                            with solara.lab.Tab("System", icon_name="mdi-access-point"):
                                solara.Markdown("System settings")
                    with solara.lab.Tab("Analytics", icon_name="mdi-chart-line"):
                        with solara.lab.Tabs(vertical=True):
                            with solara.lab.Tab("User", icon_name="mdi-account"):
                                solara.Markdown("User analytics")
                            with solara.lab.Tab("System", icon_name="mdi-access-point"):
                                solara.Markdown("System analytics")

    ```


    ### Many tabs

    If many tabs are shown, paginations arrows are shown.

    ```solara
    import solara
    import solara.lab

    tab_count = 30


    @solara.component
    def Page():
        with solara.lab.Tabs():
            for i in range(tab_count):
                with solara.lab.Tab(f"Tab {i+1}"):
                    solara.Markdown(f"Content for tab {i+1}")
    ```


    ## Arguments

     * `value`: The index of the selected tab. If `None`, the first tab is selected or it is based in the route/path.
     * `on_value`: A callback that is called when the selected tab changes.
     * `color`: The color of text in the tab headers (only for dark=False).
     * `background_color`: The background color of the tab headers.
     * `slider_color`: The color of the slider.
     * `dark`: Apply a dark theme.
     * `grow`: Whether the tabs should grow to fill the available space.
     * `vertical`: Whether the tabs are vertical.
     * `align`: The alignment of the tabs, possible values are 'left', 'start', 'center', 'right' or 'end'.
     * `lazy`: Whether the child components of the inactive tabs are rendered or not. If lazy=True, components of inactive tabs are not rendered.
     * `classes`: Additional CSS classes to apply.
     * `style`: CSS style to apply.
    """

    paths_of_routes = [child.kwargs.get("path_or_route") for child in children]
    paths = [solara.resolve_path(path_or_route, level=0) if path_or_route else None for path_or_route in paths_of_routes]
    router = solara.use_router()
    if value is None:
        if router.path in paths:
            value = paths.index(router.path)
        else:
            value = 0

    def safe_on_value(index: Optional[int]):
        if on_value and index is not None:
            on_value(index)

    reactive_value = solara.use_reactive(value, safe_on_value)
    del value

    has_content = False
    for i, child in enumerate(children):
        if not child.component == Tab:
            raise ValueError(f"Tabs children must be Tab components, but child {i} is {child.component}")
        if child.kwargs.get("children"):
            has_content = True

    def on_v_model(index: Optional[int]):
        if index is not None:
            path = paths[index]
            if path:
                router.push(path)
            reactive_value.value = index

    if align not in ["left", "start", "center", "right", "end"]:
        raise ValueError(f"Tabs align must be one of 'left', 'start', 'center', 'right', 'end', but is {align}")

    with v.Tabs(
        v_model=reactive_value.value,
        on_v_model=on_v_model,
        centered=align == "center",
        right=align in ["right", "end"],
        children=children,
        vertical=vertical,
        color=color,
        background_color=background_color,
        show_arrows=True,
        grow=grow,
        dark=dark,
    ) as tabs:
        v.TabsSlider(color=slider_color)
        if has_content:
            with v.TabsItems(v_model=reactive_value.value, on_v_model=on_v_model):
                for i, child in enumerate(children):
                    if not lazy or reactive_value.value == i:
                        v.TabItem(children=child.kwargs.get("children", []), value=i)
                    else:
                        v.TabItem(
                            value=i,
                            children=[
                                # Nice idea, but by using the widget interface the tab does not change without binding using
                                # v-model. So we would need to implement this using a vuetify template.
                                # v.SkeletonLoader(
                                #     class_="mx-auto",
                                #     max_width="300",
                                #     type="card",
                                # )
                            ],
                        )

    return tabs
