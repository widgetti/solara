"""
# Row
"""
import solara
import solara.lab
from solara.website.utils import apidoc

gap_size = solara.reactive("12px")
justify = solara.reactive("space-around")


@solara.component
def Page():
    with solara.Card("Row demo") as main:
        with solara.Column():
            solara.Text("Justify:")
            solara.ToggleButtonsSingle(justify, values=["start", "center", "end", "space-around", "space-between", "space-evenly"])
            solara.Select(
                label="Gap size",
                values=["0px", "4px", "8px", "12px", "16px", "20px", "24px"],
            ).connect(gap_size)
        with solara.Row(gap=gap_size.value, justify=justify.value):
            colors = "green red orange brown yellow pink".split()
            for color in colors:
                solara.Button(label="Solara", color=color)
    return main


__doc__ += apidoc(solara.Row.f)  # type: ignore
