import reacton.ipyvuetify as v

import solara


@solara.component
def AppIcon(open=False, on_click=None, **kwargs):
    def click(*ignore):
        on_click()

    icon = v.AppBarNavIcon(**kwargs)
    v.use_event(icon, "click", click)
    return icon


@solara.component
def AppLayout(children=[], sidebar_open=True, title="Solara"):
    """Creates a layout with a sidebar and a main content area.

    The sidebar is only added when the AppLayout has more than one child.

    ```python
    with AppLayout(title="My App"):
        with v.Card():
            ...  # sidebar content
        with v.Card():
            ...  # main content
    ```

    # Arguments

     * `children`: The children of the AppLayout. The first child is used as the sidebar content, the rest as the main content.
     * `sidebar_open`: Whether the sidebar is open or not.
     * `title`: The title of the app shown in the app bar.

    """
    sidebar_open, set_sidebar_open = solara.use_state_or_update(sidebar_open)
    use_drawer = len(children) > 1
    children_content = children
    if use_drawer:
        children_content = children[1:]
    with v.Html(tag="div", style_="height: 100vh") as main:
        with solara.HBox():
            if use_drawer:
                with v.NavigationDrawer(
                    width="min-content",
                    v_model=sidebar_open,
                    on_v_model=set_sidebar_open,
                    style_="z-index: 2; min-width: 400px; max-width: 600px",
                    clipped=True,
                    app=True,
                    disable_resize_watcher=True,
                    disable_route_watcher=True,
                ):
                    if not title:
                        AppIcon(sidebar_open, on_click=lambda: set_sidebar_open(not sidebar_open))
                    v.Html(tag="div", children=[children[0]])
            else:
                AppIcon(sidebar_open, on_click=lambda: set_sidebar_open(not sidebar_open), style_="position: absolute; z-index: 2")
        if title:
            with v.AppBar(color="primary", dark=True, app=True, clipped_left=True, hide_on_scroll=True):
                if use_drawer:
                    AppIcon(sidebar_open, on_click=lambda: set_sidebar_open(not sidebar_open))
                v.ToolbarTitle(children=[title])
                v.Spacer()
        with v.Content():
            v.Col(cols=12, children=children_content)
    return main
