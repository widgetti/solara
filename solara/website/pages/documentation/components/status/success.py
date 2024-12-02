"""# Success

Solara has 4 types of alerts:

 * Success (this page)
 * [Info](/documentation/components/status/info)
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
    solara.Success(
        f"This is solara.Success(label='...', text={text.value}, dense={dense.value}, outlined={outlined.value}, icon={icon.value})",
        text=text.value,
        dense=dense.value,
        outlined=outlined.value,
        icon=icon.value,
    )


__doc__ += apidoc(solara.Success.f)  # type: ignore
