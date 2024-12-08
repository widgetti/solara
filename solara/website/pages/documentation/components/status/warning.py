"""# Warning

Solara has 4 types of alerts:

 * [Success](/documentation/components/status/success)
 * [Info](/documentation/components/status/info)
 * Warning (this page)
 * [Error](/documentation/components/status/error)



"""

import solara
from solara.website.utils import apidoc


@solara.component
def Page():
    state = solara.use_reactive(
        {
            "icon": True,
            "dense": False,
            "outlined": True,
            "text": True,
        }
    )

    with solara.GridFixed(4):
        solara.Checkbox(label="Use icon", value=state["icon"], on_value=lambda val: state.update({"icon": val}))
        solara.Checkbox(label="Show dense", value=state["dense"], on_value=lambda val: state.update({"dense": val}))
        solara.Checkbox(label="Show as text", value=state["text"], on_value=lambda val: state.update({"text": val}))
        solara.Checkbox(label="Show outlined", value=state["outlined"], on_value=lambda val: state.update({"outlined": val}))

    solara.Warning(
        f"This is solara.Warning(label='...', text={state['text']}, dense={state['dense']}, outlined={state['outlined']}, icon={state['icon']})",
        text=state["text"],
        dense=state["dense"],
        outlined=state["outlined"],
        icon=state["icon"],
    )


__doc__ += apidoc(solara.Warning.f)  # type: ignore
