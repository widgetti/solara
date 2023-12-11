"""
# VBox

Lays out children in a vertical direction.
"""

import solara

from .common import ColorCard


@solara.component
def Page():
    with solara.VBox() as main:
        colors = "green red orange brown yellow pink".split()
        with solara.VBox():
            for color in colors:
                ColorCard(color, color)
    return main
