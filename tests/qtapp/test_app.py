import solara
import solara.lab


def callback(event):
    print("Event received:", event)


@solara.component_vue("render_test.vue")
def RenderTest(event_rendered):
    pass


@solara.component
def Page():
    RenderTest(event_rendered=callback)
    # make sure vue components of solara are working
    solara.lab.ThemeToggle()
