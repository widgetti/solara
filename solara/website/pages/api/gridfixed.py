"""
# GridFixed

Lays out children in a grid with a fixed number of columns.
"""

from solara.alias import reacton, sol

from .common import ColorCard


@reacton.component
def Page():
    with sol.VBox() as main:
        colors = "green red orange brown yellow pink".split()
        with sol.GridFixed(columns=3):
            for color in colors:
                ColorCard(color, color)
    return main
