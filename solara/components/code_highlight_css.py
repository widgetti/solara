import ipyvuetify as vy
import react_ipywidgets as react


class CodeHighlightCssWidget(vy.VuetifyTemplate):
    template_file = (__file__, "code_highlight_css.vue")


@react.component
def CodeHighlightCss():
    return CodeHighlightCssWidget.element()
