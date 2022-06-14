import ipyvuetify as vy
import traitlets

from solara.kitchensink import react


class TitleWidget(vy.VuetifyTemplate):
    template_file = (__file__, "title.vue")
    title = traitlets.Unicode().tag(sync=True)


@react.component
def Title(title: str):
    return TitleWidget.element(title=title)
