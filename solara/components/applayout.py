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
def AppLayout(children=[], navigation=None, navigation_open=True, open_right=False, title="Solara"):
    navigation_open, set_navigation_open = solara.use_state_or_update(navigation_open)
    open_right, set_open_right = solara.use_state(open_right)
    with v.Html(tag="div", style_="height: 100vh") as main:
        # with solara.VBox():
        if title:
            with v.AppBar(color="primary", dark=True, app=True, clipped_left=True):
                if navigation:
                    AppIcon(navigation_open, on_click=lambda: set_navigation_open(not navigation_open))
                v.ToolbarTitle(children=[title])
                v.Spacer()
            with solara.HBox():
                # with v.Html(tag="div"):
                if navigation:
                    with v.NavigationDrawer(
                        width="min-content",
                        v_model=navigation_open,
                        on_v_model=set_navigation_open,
                        style_="z-index: 2; min-width: 400px; max-width: 600px",
                        clipped=True,
                        app=True,
                    ):
                        if not title:
                            AppIcon(navigation_open, on_click=lambda: set_navigation_open(not navigation_open))
                        v.Html(tag="div", children=[navigation])
                else:
                    AppIcon(navigation_open, on_click=lambda: set_navigation_open(not navigation_open), style_="position: absolute; z-index: 2")

                with v.Content():
                    v.Col(cols=12, children=children)
    return main
