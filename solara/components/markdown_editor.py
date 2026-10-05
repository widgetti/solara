from typing import Callable

import ipyvuetify
import traitlets

import solara


class MarkdownEditorWidget(ipyvuetify.VuetifyTemplate):
    template_file = (__file__, "markdown_editor.vue")

    value = traitlets.Unicode("").tag(sync=True)
    height = traitlets.Unicode("180px").tag(sync=True)
    cdn = traitlets.Unicode(None, allow_none=True).tag(sync=True)

    @traitlets.default("cdn")
    def _cdn(self):
        import solara.settings

        if not solara.settings.assets.proxy:
            return solara.settings.assets.cdn


@solara.component
def MarkdownEditor(value: str = "", on_value: Callable[[str], None] = None):
    """WYSIWYG (visual) Markdown editor.

    ## Arguments

    * value: Markdown text
    * on_value: Callback function that is called when the text is changed
    """
    return MarkdownEditorWidget.element(value=value, on_value=on_value)
