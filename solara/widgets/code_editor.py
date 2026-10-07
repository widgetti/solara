from __future__ import annotations

from typing import Callable

import ipyvue
import traitlets

import solara
from solara.util import IPYVUETIFY_V3


class CodeEditorWidget(ipyvue.VueTemplate):
    template_file = (__file__, "code_editor_v3.vue" if IPYVUETIFY_V3 else "code_editor.vue")

    value = traitlets.Unicode("").tag(sync=True)
    language = traitlets.Unicode("python").tag(sync=True)
    theme = traitlets.Unicode("default").tag(sync=True)
    height = traitlets.Unicode("240px").tag(sync=True)
    read_only = traitlets.Bool(False).tag(sync=True)
    line_numbers = traitlets.Bool(True).tag(sync=True)
    tab_size = traitlets.Int(4).tag(sync=True)
    cdn = traitlets.Unicode(None, allow_none=True).tag(sync=True)

    @traitlets.default("cdn")
    def _cdn(self):
        import solara.settings

        if not solara.settings.assets.proxy:
            return solara.settings.assets.cdn


@solara.component
def CodeEditor(
    value: str = "",
    on_value: Callable[[str], None] | None = None,
    language: str = "python",
    theme: str = "default",
    height: str = "240px",
    read_only: bool = False,
    line_numbers: bool = True,
    tab_size: int = 4,
):
    """Code editor backed by CodeMirror 6.

    ## Arguments

    * value: Editor content.
    * on_value: Callback called when the content changes.
    * language: Language mode used for syntax highlighting.
    * theme: CodeMirror theme name.
    * height: Editor height.
    * read_only: Disable editing.
    * line_numbers: Show line numbers.
    * tab_size: Number of spaces for tabs.
    """

    return CodeEditorWidget.element(
        value=value,
        on_value=on_value,
        language=language,
        theme=theme,
        height=height,
        read_only=read_only,
        line_numbers=line_numbers,
        tab_size=tab_size,
    )
