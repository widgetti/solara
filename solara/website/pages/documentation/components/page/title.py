"""# Title"""

from typing import Optional, cast

import solara
from solara.website.utils import apidoc


@solara.component
def Page():
    title = solara.use_reactive(cast(Optional[str], "Custom title!"))

    solara.ToggleButtonsSingle(value=title, values=[None, "Custom title!", "Different custom title"])

    if title is not None:
        # if the title is not set in a child component, the parent's title will be used
        with solara.Head():
            # title should always occur inside a Head component
            solara.Title(title)
        solara.Info(f"Your browser tab title should say {title}", classes=["mt-4"])
    else:
        solara.Warning("If no title is set, the parent title is used.", classes=["mt-4"])


__doc__ += apidoc(solara.Title.f)  # type: ignore
