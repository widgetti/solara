import ipyvuetify as vy
import reacton


class CodeHighlightCssWidget(vy.VuetifyTemplate):
    template_file = (__file__, "code_highlight_css.vue")


@reacton.component
def CodeHighlightCss():
    return CodeHighlightCssWidget.element()
