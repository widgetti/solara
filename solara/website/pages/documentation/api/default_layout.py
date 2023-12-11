"""# DefaultLayout

"""

import solara
from solara.website.utils import apidoc

title = "DefaultLayout"


@solara.component
def Page():
    return solara.Warning("This component does not render well as a child component. If you want to see it, you should follow the multipage guide above 🙂")


__doc__ += apidoc(solara.DefaultLayout.f)  # type: ignore
