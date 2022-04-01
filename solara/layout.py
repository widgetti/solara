import react_ipywidgets as react
import react_ipywidgets.ipyvuetify as v

from solara.kitchensink import vue


@react.component
def AppIcon(open=False, on_click=None):
    def click(*ignore):
        print("click")
        on_click()

    icon = v.AppBarNavIcon()
    v.use_event(icon, "click", click)
    return icon


@react.component
def LayoutApp(content, left=None, right=None, open_left=False, open_right=False, title="Solara"):
    open_left, set_open_left = react.use_state(open_left)
    open_right, set_open_right = react.use_state(open_right)
    print(open_left)
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
            v.Col(cols=12, children=[content])
        if right:
            with v.NavigationDrawer(absolute=True, right=True, width="min-content", v_model=open_right):
                with v.Btn(icon=True) as btn:
                    vue.use_event(btn, "click", lambda *_ignore: set_open_right(not open_right))
                    v.Icon(children=["mdi-settings"])
                with v.Html(tag="div", children=[right]):
                    pass
    return main
