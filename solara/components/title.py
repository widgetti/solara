import ipyvuetify as vy
import solara
import traitlets


class TitleWidget(vy.VuetifyTemplate):
    template_file = (__file__, "title.vue")
    title = traitlets.Unicode().tag(sync=True)


@solara.component
def Title(title: str):
    return TitleWidget.element(title=title)
