"""# Title
"""

from typing import Optional, cast

import solara
from solara.website.utils import apidoc


@solara.component
def Page():
    title, set_title = solara.use_state(cast(Optional[str], "Custom title!"))
    with solara.VBox() as main:
        solara.ToggleButtonsSingle(value=title, values=[None, "Custom title!", "Different custom title"], on_value=set_title)

        if title is not None:
            # if the title is not set in a child component, the parent's title will be used
            with solara.Head():
                # title should always occur inside a Head component
                solara.Title(title)
            solara.Info(f"Your browser tab title should say {title}", classes=["mt-4"])
        else:
            solara.Warning("If no title is set, the parent title is used.", classes=["mt-4"])

    return main


__doc__ += apidoc(solara.Title.f)  # type: ignore
