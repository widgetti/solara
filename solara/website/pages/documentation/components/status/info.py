"""# Info

Solara has 4 types of alerts:

 * [Success](/documentation/components/status/success)
 * Info (this page)
 * [Warning](/documentation/components/status/warning)
 * [Error](/documentation/components/status/error)



"""

import solara
from solara.website.utils import apidoc


@solara.component
def Page():
    icon = solara.use_reactive(True)
    dense = solara.use_reactive(False)
    outlined = solara.use_reactive(True)
    text = solara.use_reactive(True)

    with solara.GridFixed(4):
        solara.Checkbox(label="Use icon", value=icon)
        solara.Checkbox(label="Show dense", value=dense)
        solara.Checkbox(label="Show as text", value=text)
        solara.Checkbox(label="Show outlined", value=outlined)
    solara.Info(
        f"This is solara.Info(label='...', text={text.value}, dense={dense.value}, outlined={outlined.value}, icon={icon.value})",
        text=text.value,
        dense=dense.value,
        outlined=outlined.value,
        icon=icon.value,
    )


__doc__ += apidoc(solara.Info.f)  # type: ignore
