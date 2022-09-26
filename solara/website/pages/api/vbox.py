"""
# VBox

Lays out children in a vertical direction.
"""

from solara.alias import reacton, sol

from .common import ColorCard


@reacton.component
def Page():
    with sol.VBox() as main:
        colors = "green red orange brown yellow pink".split()
        with sol.VBox():
            for color in colors:
                ColorCard(color, color)
    return main
