"""# Head"""

import solara
from solara.website.utils import apidoc


@solara.component
def Page():
    solara.Info("A Head component does not render somesome visual on the page, but it is used to avoid duplicate tags, such as titles.")
    with solara.Head():
        # title should always occur inside a Head component
        solara.Title("Custom title")


__doc__ += apidoc(solara.Head.f)  # type: ignore
