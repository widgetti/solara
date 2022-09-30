from typing import Callable

import ipyvuetify
import solara
import traitlets


class MarkdownEditorWidget(ipyvuetify.VuetifyTemplate):
    template_file = (__file__, "markdown_editor.vue")

    value = traitlets.Unicode("").tag(sync=True)
    height = traitlets.Unicode("180px").tag(sync=True)


@solara.component
def MarkdownEditor(value: str = "", on_value: Callable[[str], None] = None):
    return MarkdownEditorWidget.element(value=value, on_value=on_value)
