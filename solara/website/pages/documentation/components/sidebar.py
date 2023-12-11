"""
# Sidebar

"""
import solara
import solara.lab
from solara.website.utils import apidoc


@solara.component
def Page():
    return solara.Markdown(
        """

    The sidebar can only be shown in embedded mode on this page.
    Visit the [Scatter app demo](/apps/scatter) to see an example of a full sidebar used in Soalra server.

    [![AppLayout screenshot](https://dxhl76zpt6fap.cloudfront.net/public/docs/app-layout.webp)](/apps/scatter)
    """
    )


__doc__ += apidoc(solara.Sidebar.f)  # type: ignore
