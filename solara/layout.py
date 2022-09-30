import reacton.ipyvuetify as v
import solara
from solara.kitchensink import vue


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
            with v.NavigationDrawer(absolute=True, right=False, width="min-content", v_model=open_left):
                AppIcon(open_left, on_click=lambda: set_open_left(not open_left))
                with v.Html(tag="div", children=[left]):
                    pass
        with v.Toolbar(dense=True, class_="elevation-3", dark=False):
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
            with v.NavigationDrawer(absolute=True, right=True, width="min-content", v_model=open_right):
                with v.Btn(icon=True) as btn:
                    vue.use_event(btn, "click", lambda *_ignore: set_open_right(not open_right))
                    v.Icon(children=["mdi-settings"])
                with v.Html(tag="div", children=[right]):
                    pass
    return main
