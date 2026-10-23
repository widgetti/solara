import ipyvue
import ipyvuetify as vy
import solara
from solara.server import frontend


class CodeHighlightCssWidgetVue(ipyvue.VueTemplate):
    template_file = (__file__, "code_highlight_css.vue")


class CodeHighlightCssWidget(CodeHighlightCssWidgetVue, vy.VuetifyTemplate):
    pass


@solara.component
def CodeHighlightCss():
    return frontend.template_class(CodeHighlightCssWidget, CodeHighlightCssWidgetVue).element()
