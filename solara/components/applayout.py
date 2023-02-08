from typing import Callable, Dict, List, Tuple, cast

import reacton
import reacton.core
import reacton.ipyvuetify as v
import reacton.utils
from reacton.core import Element

import solara
import solara.lab

from . import title as t


@solara.component
def AppIcon(open=False, on_click=None, **kwargs):
    def click(*ignore):
        on_click()

    icon = v.AppBarNavIcon(**kwargs)
    v.use_event(icon, "click", click)
    return icon


should_use_embed = solara.create_context(False)
PortalElements = Dict[str, List[Tuple[int, Element]]]


def _set_sidebar_default(updater: Callable[[PortalElements], PortalElements]):
    pass


class ElementPortal:
    def __init__(self):
        self.context = solara.create_context((cast(PortalElements, {}), _set_sidebar_default))

    # TODO: can we generalize the use of 'portals' ? (i.e. transporting elements from one place to another)
    def use_portal(self) -> List[Element]:
        portal_elements, set_portal_elements = solara.use_state(cast(PortalElements, {}))
        self.context.provide((portal_elements, set_portal_elements))  # type: ignore

        portal_elements_flat: List[Tuple[int, Element]] = []
        for uuid, value in portal_elements.items():
            portal_elements_flat.extend(value)
        portal_elements_flat.sort(key=lambda x: x[0])
        return [e[1] for e in portal_elements_flat]

    def use_portal_add(self, children: List[Element], offset: int):
        key = solara.use_unique_key(prefix="portal-")
        portal_elements, set_portal_elements = solara.use_context(self.context)
        values: List[Tuple[int, Element]] = []
        for i, child in enumerate(children):
            values.append((offset + i, child))

        # updates we do when children/offset changes
        def add():
            # we use the update function method, to avoid stale data
            def update_dict(portal_elements):
                portal_elements_updated = portal_elements.copy()
                portal_elements_updated[key] = values
                return portal_elements_updated

            set_portal_elements(update_dict)

        solara.use_effect(add, [values])

        # cleanup we only need to do after component removal
        def add_cleanup():
            def cleanup():
                def without(portal_elements):
                    portal_elements_restored = portal_elements.copy()
                    portal_elements_restored.pop(key, None)
                    return portal_elements_restored

                set_portal_elements(without)

            return cleanup

        solara.use_effect(add_cleanup, [])


sidebar_portal = ElementPortal()
appbar_portal = ElementPortal()


@solara.component
def AppBar(children=[]):
    """Puts its children in the app bar of the AppLayout (or any layout that supports it).
    This component does not need to be a direct child of the AppLayout, it can be at any level in your component tree.

    ## Example showing an app bar
    ```solara
    import solara

    @solara.component
    def Page():
        logged_in, set_logged_in = solara.use_state(False)
        def toggle_login():
            set_logged_in(not logged_in)

        with solara.AppBar():
            icon_name = "mdi-logout" if logged_in else "mdi-login"
            solara.Button(icon_name=icon_name , on_click=toggle_login, icon=True)
        with solara.Column():
            if logged_in:
                solara.Info("You are logged in")
            else:
                solara.Error("You are logged out")
    ```
    """
    # TODO: generalize this, this is also used in title
    level = 0
    rc = reacton.core.get_render_context()
    context = rc.context
    while context and context.parent:
        level += 1
        context = context.parent
    offset = 2**level
    appbar_portal.use_portal_add(children, offset)

    return solara.Div(style="display; none")


@solara.component
def Sidebar(children=[]):
    """Puts its children in the sidebar of the AppLayout (or any layout that supports it).
    This component does not need to be a direct child of the AppLayout, it can be at any level in your component tree.

    On the solara.dev website and in the Jupyter notebook, the sidebar is shown in a dialog instead (embedded mode)

    ## Example showing a sidebar (embedded mode)
    ```solara
    import solara

    @solara.component
    def Page():
        with solara.Column() as main:
            with solara.Sidebar():
                solara.Markdown("## I am in the sidebar")
                solara.SliderInt(label="Ideal for placing controls")
            solara.Info("I'm in the main content area, put your main content here")
        return main
    ```


    """
    # TODO: generalize this, this is also used in title
    level = 0
    rc = reacton.core.get_render_context()
    context = rc.context
    while context and context.parent:
        level += 1
        context = context.parent
    offset = 2**level
    sidebar_portal.use_portal_add(children, offset)

    return solara.Div(style="display; none")


@solara.component
def AppLayout(
    children=[],
    sidebar_open=True,
    title=None,
    navigation=True,
    toolbar_dark=True,
):
    """The default layout for Solara apps. It consists of an toolbar bar, a sidebar and a main content area.

     * The title of the app is set using the [Title](/api/title) component.
     * The sidebar content is set using the [Sidebar](/api/sidebar) component.
     * The content is set by the `Page` component provided by the user.

    This component is usually not used directly, but rather through via the [Layout system](/docs/howto/layout).

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
     * `title`: The title of the app shown in the app bar, can also be set using the [Title](/api/title) component.
     * `toolbar_dark`: Whether the toolbar should be dark or not.
     * `navigation`: Whether the navigation tabs based on routing should be shown.

    """
    route, routes = solara.use_route()
    paths = [solara.resolve_path(r, level=0) for r in routes]
    location = solara.use_context(solara.routing._location_context)
    embedded_mode = solara.use_context(should_use_embed)
    fullscreen, set_fullscreen = solara.use_state(False)
    # we cannot nest AppLayouts, so we can use the context to set the embedded mode
    should_use_embed.provide(True)
    index = routes.index(route) if route else None

    sidebar_open, set_sidebar_open = solara.use_state_or_update(sidebar_open)
    # remove the appbar from the children
    children_without_portal_sources = [c for c in children if c.component != AppBar]
    use_drawer = len(children_without_portal_sources) > 1
    children_content = children
    children_sidebar = []
    if use_drawer:
        child_sidebar = children_without_portal_sources.pop(0)
        children_sidebar = [child_sidebar]
        children_content = [c for c in children if c is not child_sidebar]
    children_sidebar = children_sidebar + sidebar_portal.use_portal()
    children_appbar = appbar_portal.use_portal()
    if children_sidebar:
        use_drawer = True

    title = t.use_title_get() or title

    show_app_bar = title or routes or children_appbar or use_drawer
    if not show_app_bar and not children_sidebar and len(children) == 1:
        return children[0]
    if embedded_mode and not fullscreen:
        # this version doesn't need to run fullscreen
        # also ideal in jupyter notebooks
        with v.Html(tag="div") as main:
            if show_app_bar or use_drawer:

                def set_path(index):
                    path = paths[index]
                    location.pathname = path

                v_slots = []
                if routes and navigation and len(routes) > 1:
                    with v.Tabs(v_model=index, on_v_model=set_path, centered=True) as tabs:
                        for route in routes:
                            name = route.path if route.path != "/" else "Home"
                            v.Tab(children=[name])
                    v_slots = [{"name": "extension", "children": tabs}]
                with v.AppBar(color="primary" if toolbar_dark else None, dark=toolbar_dark, v_slots=v_slots):
                    if use_drawer:
                        icon = AppIcon(sidebar_open, on_click=lambda: set_sidebar_open(not sidebar_open), v_on="x.on")
                        with v.Menu(
                            offset_y=True,
                            nudge_left="50px",
                            left=True,
                            v_slots=[{"name": "activator", "variable": "x", "children": [icon]}],
                            close_on_content_click=False,
                        ):
                            pass
                            v.Html(tag="div", children=children_sidebar, style_="background-color: white; padding: 12px; min-width: 400px")
                    if title:
                        v.ToolbarTitle(children=[title])
                    v.Spacer()
                    for child in children_appbar:
                        solara.display(child)
                    solara.Button(icon_name="mdi-fullscreen", on_click=lambda: set_fullscreen(True), icon=True, dark=False)
            with v.Row(no_gutters=False):
                v.Col(cols=12, children=children_content)
    else:
        with v.Html(tag="div", style_="min-height: 100vh") as main:
            with solara.HBox():
                if use_drawer:
                    with v.NavigationDrawer(
                        width="min-content",
                        v_model=sidebar_open,
                        on_v_model=set_sidebar_open,
                        style_="z-index: 2; min-width: 400px; max-width: 600px",
                        clipped=True,
                        app=True,
                        # disable_resize_watcher=True,
                        disable_route_watcher=True,
                        mobile_break_point="960",
                    ):
                        if not show_app_bar:
                            AppIcon(sidebar_open, on_click=lambda: set_sidebar_open(not sidebar_open))
                        v.Html(tag="div", children=children_sidebar, style_="padding: 12px;").meta(ref="sidebar-content")
                else:
                    AppIcon(sidebar_open, on_click=lambda: set_sidebar_open(not sidebar_open), style_="position: absolute; z-index: 2")
            if show_app_bar:

                def set_path(index):
                    path = paths[index]
                    location.pathname = path

                v_slots = []
                if routes and navigation and len(routes) > 1:
                    with v.Tabs(v_model=index, on_v_model=set_path, centered=True) as tabs:
                        for route in routes:
                            name = route.path if route.path != "/" else "Home"
                            v.Tab(children=[name])
                    v_slots = [{"name": "extension", "children": tabs}]
                # if hide_on_scroll is True, and we have a little bit of scrolling, vuetify seems to act strangely
                # when scolling (on @mariobuikhuizen/vuetify v2.2.26-rc.0
                with v.AppBar(color="primary", dark=True, app=True, clipped_left=True, hide_on_scroll=False, v_slots=v_slots):
                    if use_drawer:
                        AppIcon(sidebar_open, on_click=lambda: set_sidebar_open(not sidebar_open))
                    if title:
                        v.ToolbarTitle(children=[title])
                    v.Spacer()
                    for child in children_appbar:
                        solara.display(child)
                    if fullscreen:
                        solara.Button(icon_name="mdi-fullscreen-exit", on_click=lambda: set_fullscreen(False), icon=True, dark=False)

            with v.Content():
                v.Col(cols=12, children=children_content)
        if fullscreen:
            with v.Dialog(v_model=True, children=[], fullscreen=True, hide_overlay=True) as dialog:
                v.Sheet(class_="overflow-y-auto overflow-x-auto", children=[main])
                pass
            return dialog
    return main


@solara.component
def _AppLayoutEmbed(children=[], sidebar_open=True, title=None):
    """Forces the embed more for a AppLayout. This is used by default in Jupyter."""
    should_use_embed.provide(True)
    return AppLayout(children=children, sidebar_open=sidebar_open, title=title)


reacton.core.jupyter_decorator_components.append(_AppLayoutEmbed)
