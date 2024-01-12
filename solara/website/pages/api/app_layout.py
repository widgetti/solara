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
    An example cannot be shown embedded in this page, Visit the [AppLayout page](/apps/scatter) to see an example.

    [![AppLayout screenshot](https://dxhl76zpt6fap.cloudfront.net/public/docs/app-layout.webp)](/apps/scatter)
    """
    )


__doc__ += apidoc(solara.AppLayout.f)  # type: ignore
