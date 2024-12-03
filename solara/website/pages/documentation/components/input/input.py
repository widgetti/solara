"""# Input fields

This page contains all the input fields available in Solara.

# InputText
"""

import solara
from solara.website.components import NoPage
from solara.website.utils import apidoc

Page = NoPage


__doc__ += apidoc(solara.InputText.f)  # type: ignore
__doc__ += "# InputTextArea"
__doc__ += apidoc(solara.InputTextArea.f)  # type: ignore
__doc__ += "# InputFloat"
__doc__ += apidoc(solara.InputFloat.f)  # type: ignore
__doc__ += "# InputInt"
__doc__ += apidoc(solara.InputInt.f)  # type: ignore

__doc__ += """
# Autofocus Example

```solara
import solara
import solara.lab


@solara.component
def Page():
    show_dialog = solara.use_reactive(False)
    show_conditional = solara.use_reactive(False)
    with solara.Row():
        solara.Button("Show dialog", on_click=lambda: show_dialog.set(True))
        solara.Button("Show conditionally rendered element", on_click=lambda: show_conditional.set(not show_conditional.value))
    with solara.lab.ConfirmationDialog(open=show_dialog):
        solara.InputFloat("Float here", autofocus=True)
    if show_conditional.value:
        solara.InputFloat("Float here", autofocus=True)
```
"""
