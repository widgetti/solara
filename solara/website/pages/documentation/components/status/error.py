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
    icon, set_icon = solara.use_state(True)
    dense, set_dense = solara.use_state(False)
    outlined, set_outlined = solara.use_state(True)
    text, set_text = solara.use_state(True)
 
    with solara.GridFixed(4):
        solara.Checkbox(label="Use icon", value=icon, on_value=set_icon)
        solara.Checkbox(label="Show dense", value=dense, on_value=set_dense)
        solara.Checkbox(label="Show as text", value=text, on_value=set_text)
        solara.Checkbox(label="Show outlined", value=outlined, on_value=set_outlined)
    solara.Error(
        f"This is solara.Error(label='...', text={text}, dense={dense}, outlined={outlined}, icon={icon})",
        text=text,
        dense=dense,
        outlined=outlined,
        icon=icon,
    )



__doc__ += apidoc(solara.Error.f)  # type: ignore
