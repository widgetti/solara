"""
# HBox
Lays out children in horizontal direction.
"""

import solara

from ..common import ColorCard


@solara.component
def Page():
    colors = "green red orange brown yellow pink".split()
    with solara.Row():
        for color in colors:
            ColorCard(color, color)
