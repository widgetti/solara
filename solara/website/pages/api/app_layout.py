"""
# AppLayout

"""
import solara
import solara.lab
from solara.website.utils import apidoc

title = "AppLayout"


@solara.component
def Page():
    return solara.Markdown(
        """
    An example cannot be shown embeddded in this page, Visit the [AppLayout page](/app/scatterapp) to see an example.

    [![AppLayout screenshot](/static/public/docs/app-layout.png)](/app/scatterapp)
    """
    )


__doc__ += apidoc(solara.AppLayout.f)  # type: ignore
