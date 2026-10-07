"""
# Scrollable

Use `Scrollable` to constrain long content to a vertically scrollable container.
"""

import solara
from solara.website.utils import apidoc


@solara.component
def Page():
    with solara.Scrollable(max_height="250px"):
        solara.Markdown("\n\n".join(f"## Section {number}\n\nScrollable content." for number in range(1, 11)))


__doc__ += apidoc(solara.Scrollable.f)  # type: ignore
