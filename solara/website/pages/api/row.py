"""
# Row
"""
import solara
import solara.lab
from solara.website.utils import apidoc

from .common import ColorCard

gap_size = solara.lab.Reactive[str]("12px")


@solara.component
def Page():
    gap_size.use()

    with solara.Card("Row demo") as main:
        with solara.Row():
            solara.Select(
                label="Gap size",
                values=["0px", "4px", "8px", "12px", "16px", "20px", "24px"],
            ).connect(gap_size)
        with solara.Row(gap=gap_size.value):
            colors = "green red orange brown yellow pink".split()
            for color in colors:
                ColorCard(color, color)
    return main


__doc__ += apidoc(solara.Row.f)  # type: ignore
