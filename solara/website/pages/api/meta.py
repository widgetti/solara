"""# Meta
"""

import solara
from solara.website.utils import apidoc


@solara.component
def Page():
    with solara.VBox() as main:
        solara.Info("Nothing to see here, only in this page's source code, or by looking at the google search results for this page.")
        with solara.Head():
            solara.Meta(
                name="description",
                content="The Meta component can be used to set the description of a page. This is useful for SEO, or crawlers that index your page.",
            )

    return main


__doc__ += apidoc(solara.Meta.f)  # type: ignore
