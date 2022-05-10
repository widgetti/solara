"""
# GridFixed

Lays out children in a grid with a fixed number of columns.
"""

from solara.kitchensink import react, sol

from .common import ColorCard


@react.component
def GridFixedDemo():
    with sol.VBox() as main:
        colors = "green red orange brown yellow pink".split()
        with sol.GridFixed(columns=3):
            for color in colors:
                ColorCard(color, color)
    return main


Component = sol.GridFixed
App = GridFixedDemo
