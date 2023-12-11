"""
# GridDraggable

Child components are laid out on a grid, which can be dragged and resized.
"""
import pprint
import textwrap

import solara

from .common import ColorCard

title = "GridDraggable"


@solara.component
def Page():
    grid_layout_initial = [
        {"h": 5, "i": "0", "moved": False, "w": 3, "x": 0, "y": 0},
        {"h": 5, "i": "1", "moved": False, "w": 5, "x": 3, "y": 0},
        {"h": 11, "i": "2", "moved": False, "w": 4, "x": 8, "y": 0},
        {"h": 12, "i": "3", "moved": False, "w": 5, "x": 0, "y": 5},
        {"h": 6, "i": "4", "moved": False, "w": 3, "x": 5, "y": 5},
        {"h": 6, "i": "5", "moved": False, "w": 7, "x": 5, "y": 11},
    ]

    colors = "green red orange brown yellow pink".split()

    # we need to store the state of the grid_layout ourselves, otherwise it will 'reset'
    # each time we change resizable or draggable
    grid_layout, set_grid_layout = solara.use_state(grid_layout_initial)

    # some placeholders
    items = [ColorCard(title=f"Child {i}", color=colors[i]) for i in range(len(grid_layout))]
    with solara.VBox() as main:
        resizable = solara.ui_checkbox("Allow resizing", value=True)
        draggable = solara.ui_checkbox("Allow dragging", value=True)

        def reset_layout():
            set_grid_layout(grid_layout_initial)

        solara.Button("Reset to initial layout", on_click=reset_layout)

        solara.GridDraggable(items=items, grid_layout=grid_layout, resizable=resizable, draggable=draggable, on_grid_layout=set_grid_layout)

        # some string kung fu to make this print nicely
        grid_layout_formatted = pprint.pformat(grid_layout, indent=4)
        grid_layout_formatted = textwrap.indent(grid_layout_formatted, " " * len("grid_layout = "))
        grid_layout_formatted = grid_layout_formatted[len("grid_layout = ") :]
        solara.Markdown(
            f"""
            # Resulting layout

            This layout can be copy pasted to put in your code as an initial layout:

            ```python
            grid_layout = {grid_layout_formatted}
            ```
            """
        )
    return main
