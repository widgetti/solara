from typing import Callable

import ipyvuetify
import react_ipywidgets as react
import traitlets


class MarkdownEditorWidget(ipyvuetify.VuetifyTemplate):
    template_file = (__file__, "markdown_editor.vue")

    value = traitlets.Unicode("").tag(sync=True)
    height = traitlets.Unicode("180px").tag(sync=True)


@react.component
def MarkdownEditor(value: str = "", on_value: Callable[[str], None] = None):
    return MarkdownEditorWidget.element(value=value, on_value=on_value)
