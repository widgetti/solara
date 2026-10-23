import ipyvuetify as vy
import reacton.core
import solara


class CodeHighlightCssWidget(vy.VuetifyTemplate):
    template_file = (__file__, "code_highlight_css.vue")


@solara.component
def CodeHighlightCss() -> reacton.core.Element[CodeHighlightCssWidget]:
    return CodeHighlightCssWidget.element()
