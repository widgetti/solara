"""# Checkbox

"""

import solara
from solara.website.utils import apidoc


@solara.component
def Page():
    turbo_boost, set_turbo_boost = solara.use_state(True)
    with solara.VBox() as main:
        if turbo_boost:
            solara.Success("Turbo boost is on")
        else:
            solara.Warning("Turbo boost is off, you might want to turn it on")
        solara.Checkbox(label="Turbo boost", value=turbo_boost, on_value=set_turbo_boost)
    return main


__doc__ += apidoc(solara.Checkbox.f)  # type: ignore
