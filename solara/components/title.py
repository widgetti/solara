import ipyvuetify as vy
import reacton
import traitlets


class TitleWidget(vy.VuetifyTemplate):
    template_file = (__file__, "title.vue")
    title = traitlets.Unicode().tag(sync=True)


@reacton.component
def Title(title: str):
    return TitleWidget.element(title=title)
