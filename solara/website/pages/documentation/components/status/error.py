"""# Error

Solara has 4 types of alerts:

 * [Success](/documentation/components/status/success)
 * [Info](/documentation/components/status/info)
 * [Warning](/documentation/components/status/warning)
 * Error (this page)



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
    solara.Error(
        f"This is solara.Error(label='...', text={text}, dense={dense}, outlined={outlined}, icon={icon})",
        text=text,
        dense=dense,
        outlined=outlined,
        icon=icon,
    )


__doc__ += apidoc(solara.Error.f)  # type: ignore
