"""
# GridFixed

Lays out children in a grid with a fixed number of columns.
"""

import solara

from .common import ColorCard

title = "GridFixed"


@solara.component
def Page():
    with solara.VBox() as main:
        colors = "green red orange brown yellow pink".split()
        with solara.GridFixed(columns=3):
            for color in colors:
                ColorCard(color, color)
    return main
