"""
# Column
"""
import solara
import solara.lab
from solara.website.utils import apidoc

gap_size = solara.reactive("12px")
align = solara.reactive("stretch")


@solara.component
def Page():
    with solara.Card("Column demo") as main:
        with solara.Column():
            solara.Text("Align:")
            solara.ToggleButtonsSingle(align, values=["start", "center", "end", "stretch"])
            solara.Select(
                label="Gap size",
                values=["0px", "4px", "8px", "12px", "16px", "20px", "24px"],
            ).connect(gap_size)
        with solara.Column(gap=gap_size.value, align=align.value):
            colors = "green red orange brown yellow pink".split()
            for color in colors:
                solara.Button("Solara", color=color)
    return main


__doc__ += apidoc(solara.Column.f)  # type: ignore
