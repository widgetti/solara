import reacton.ipyvuetify as v
import solara
from solara.kitchensink import vue
from solara.util import IPYVUETIFY_V3


@solara.component
def AppIcon(open=False, on_click=None):
    def click(*ignore):
        on_click()

    icon = v.AppBarNavIcon()
    v.use_event(icon, "click", click)
    return icon


@solara.component
def LayoutApp(children=[], left=None, right=None, open_left=False, open_right=False, title="Solara"):
    open_left, set_open_left = solara.use_state(open_left)
    open_right, set_open_right = solara.use_state(open_right)
    with v.Html(tag="div") as main:
        if left:
            if IPYVUETIFY_V3:
                drawer = v.NavigationDrawer(absolute=True, location="left", width="min-content", v_model=open_left)
            else:
                drawer = v.NavigationDrawer(absolute=True, right=False, width="min-content", v_model=open_left)
            with drawer:
                AppIcon(open_left, on_click=lambda: set_open_left(not open_left))
                with v.Html(tag="div", children=[left]):
                    pass
        if IPYVUETIFY_V3:
            toolbar = v.Toolbar(density="compact", class_="elevation-3")
        else:
            toolbar = v.Toolbar(dense=True, class_="elevation-3", dark=False)
        with toolbar:
            if left:
                AppIcon(open_left, on_click=lambda: set_open_left(not open_left))
            v.ToolbarTitle(children=[title])
            v.Spacer()
            if right:
                with v.Btn(icon=True) as btn:
                    vue.use_event(btn, "click", lambda *_ignore: set_open_right(not open_right))
                    v.Icon(children=["mdi-settings"])
        with v.Row():
            v.Col(cols=12, children=[*children])
        if right:
            if IPYVUETIFY_V3:
                drawer = v.NavigationDrawer(absolute=True, location="right", width="min-content", v_model=open_right)
            else:
                drawer = v.NavigationDrawer(absolute=True, right=True, width="min-content", v_model=open_right)
            with drawer:
                with v.Btn(icon=True) as btn:
                    vue.use_event(btn, "click", lambda *_ignore: set_open_right(not open_right))
                    v.Icon(children=["mdi-settings"])
                with v.Html(tag="div", children=[right]):
                    pass
    return main
