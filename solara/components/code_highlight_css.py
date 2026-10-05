import ipyvuetify as vy
import solara


class CodeHighlightCssWidget(vy.VuetifyTemplate):
    template_file = (__file__, "code_highlight_css.vue")


@solara.component
def CodeHighlightCss():
    return CodeHighlightCssWidget.element()
