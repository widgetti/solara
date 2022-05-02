import pprint
import textwrap
from typing import Any, Dict, Optional, cast

import vaex

import solara as sol
import solara.components.datatable
from solara.kitchensink import react, v, vue

df = vaex.datasets.titanic()


@react.component
def DataTableDemo():
    column, set_column = react.use_state(cast(Optional[str], None))
    cell, set_cell = react.use_state(cast(Dict[str, Any], {}))

    def on_action_column(column):
        set_column(column)

    def on_action_cell(column, row_index):
        set_cell(dict(column=column, row_index=row_index))

    column_actions = [sol.ColumnAction(icon="mdi-sunglasses", name="User column action", on_click=on_action_column)]
    cell_actions = [sol.CellAction(icon="mdi-white-balance-sunny", name="User cell action", on_click=on_action_cell)]
    with sol.Div() as main:
        sol.MarkdownIt(
            f"""
# DataTable

The DataTable component can render dataframes of any size due to pagination.

## API

### Component signature
```python
@react.component
def DataTable(df, page=0, items_per_page=20, format=None, column_actions: List[ColumnAction] = [], cell_actions: List[CellAction] = []):
    ...
```

### arguments

   * `df` - `DataFrame`

### events

   * `column_actions` - Triggered via clicking on the triple dot icon on the headers (visible when hovering).
   * `cell_actions` -  Triggered via clicking on the triple dot icon in the cell (visible when hovering).

## Demo

Below we show display the titanic dataset, and demonstrate a user colum and cell action. Try clicking on the triple icon when hovering
above a column or cell. And see the following values changes:

   * Column action on: `{column}`
   * Cell action on: `{cell}`

        """
        )
        sol.components.datatable.DataTable(df, column_actions=column_actions, cell_actions=cell_actions)
    return main


@react.component
def ColorCard(title, color):
    with v.Card(style_=f"background-color: {color}; width: 100%; height: 100%") as main:
        v.CardTitle(children=[title])
    return main


@react.component
def GridFixedDemo():
    with sol.VBox() as main:
        sol.Markdown(
            """
# GridFixed

Lays out children in a grid with a fixed number of columns.
        """
        )

        colors = "green red orange brown yellow pink".split()
        with sol.GridFixed(columns=3):
            for color in colors:
                ColorCard(color, color)
    return main


@react.component
def VBoxDemo():
    with sol.VBox() as main:
        sol.Markdown(
            """
# VBox

Lays out children in a vertical direction.
        """
        )

        colors = "green red orange brown yellow pink".split()
        with sol.VBox():
            for color in colors:
                ColorCard(color, color)
    return main


@react.component
def HBoxDemo():
    with sol.VBox() as main:
        sol.Markdown(
            """
# HBox

Lays out children in horizontal direction.
        """
        )

        colors = "green red orange brown yellow pink".split()
        with sol.HBox():
            for color in colors:
                ColorCard(color, color)
    return main


@react.component
def GridDraggableDemo():
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
    grid_layout, set_grid_layout = react.use_state(grid_layout_initial)

    # some placeholders
    items = [ColorCard(title=f"Child {i}", color=colors[i]) for i in range(len(grid_layout))]
    # with sol.Div() as main:
    with sol.VBox() as main:
        # with sol.Div()
        # with v.Card(class_="pa-4", elevation=0) as main:
        sol.Markdown(
            """
# GridDraggable

Child components are layed out on a grid, which can be dragged and resized.
"""
        )
        resizable = sol.ui_checkbox(True, "Allow resizing")
        draggable = sol.ui_checkbox(True, "Allow dragging")
        btn = v.Btn(children=["Reset to initial layout"])

        def reset_layout(*ignore):
            set_grid_layout(grid_layout_initial)

        vue.use_event(btn, "click", reset_layout)
        sol.GridDraggable(items=items, grid_layout=grid_layout, resizable=resizable, draggable=draggable, on_grid_layout=set_grid_layout)

        # some string kung fu to make this print nicely
        grid_layout_formatted = pprint.pformat(grid_layout, indent=4)
        grid_layout_formatted = textwrap.indent(grid_layout_formatted, " " * len("grid_layout = "))
        grid_layout_formatted = grid_layout_formatted[len("grid_layout = ") :]
        sol.MarkdownIt(
            f"""
# Resulting layout

This layout can be copy pasted to put in your code as an initial layout:

```python
grid_layout = {grid_layout_formatted}
```
"""
        )
    return main


components = {
    "DataTable": DataTableDemo,
    "GridDraggable": GridDraggableDemo,
    "GridFixed": GridFixedDemo,
    "VBox": VBoxDemo,
    "HBox": HBoxDemo,
}


@react.component
def Components():
    tab, set_tab = react.use_state(0, "tab")
    selected, on_selected = react.use_state("Overview")
    print("selected", selected)
    with sol.HBox(grow=True) as main:
        with v.NavigationDrawer(right=False, width="min-content", v_model=True, permanent=True):
            with v.List(dense=True):
                with v.ListItemGroup(v_model=selected, on_v_model=on_selected):
                    sol.ListItem("Overview")
                    with sol.ListItem("Input", icon_name="mdi-chevron-left-box"):
                        sol.ListItem("Slider")
                        sol.ListItem("Button")
                    with sol.ListItem("Output", icon_name="mdi-chevron-right-box"):
                        sol.ListItem("Markdown")
                        sol.ListItem("HTML")
                        sol.ListItem("Image")
                        sol.ListItem("Code")
                    with sol.ListItem("Viz", icon_name="mdi-chart-histogram"):
                        sol.ListItem("FigurePlotly")
                        sol.ListItem("AltairChart")
                    with sol.ListItem("Layout", icon_name="mdi-page-layout-sidebar-left"):
                        sol.ListItem("HBox")
                        sol.ListItem("VBox")
                        sol.ListItem("GridDraggable")
                        sol.ListItem("GridFixed")
                        sol.ListItem("App")
                    with sol.ListItem("Data", icon_name="mdi-database"):
                        sol.ListItem("DataTable")
                    with sol.ListItem("Hooks", icon_name="mdi-hook"):
                        sol.ListItem("use_fetch")
                        sol.ListItem("use_json")
                    with sol.ListItem("Types", icon_name="mdi-fingerprint"):
                        sol.ListItem("Action")
                        sol.ListItem("ColumnAction")

        # with v.Card(class_="d-flex", style_="flex-grow: 1", elevation=0) as main:
        with sol.HBox(grow=True):
            with sol.Padding(4):
                if selected in components:
                    components[selected]()

    return main


app = Components()
