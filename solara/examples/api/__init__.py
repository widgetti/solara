import inspect

from solara.kitchensink import react, sol, v

from . import button, datatable, griddraggable, gridfixed, hbox, html, markdown, vbox

modules = {
    "Button": button,
    "DataTable": datatable,
    "GridDraggable": griddraggable,
    "GridFixed": gridfixed,
    "VBox": vbox,
    "HBox": hbox,
    "Markdown": markdown,
    "HTML": html,
}


@react.component
def API():
    tab, set_tab = react.use_state(0, "tab")
    selected, on_selected = react.use_state("Overview")
    print("selected", selected)
    with sol.HBox(grow=True) as main:
        with v.NavigationDrawer(right=False, width="min-content", v_model=True, permanent=True):
            with v.List(dense=True):
                with v.ListItemGroup(v_model=selected, on_v_model=on_selected):
                    sol.ListItem("Overview")
                    with sol.ListItem("Input", icon_name="mdi-chevron-left-box"):
                        # sol.ListItem("Slider")
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
                if selected in modules:
                    WithCode(modules[selected])

    return main


@react.component
def WithCode(module):
    component = module.App
    show_code, set_show_code = react.use_state(False)
    with v.Sheet() as main:
        with v.Dialog(v_model=show_code, on_v_model=set_show_code):
            with v.Sheet(class_="pa-4"):
                code = inspect.getsource(component.f)
                code = code.replace("```", "~~~")
                pre = ""
                sol.MarkdownIt(
                    f"""
```python
{pre}{code}
```
"""
                )
        # It renders code better
        sol.MarkdownIt(module.__doc__)
        sol.Button("Show code", on_click=lambda: set_show_code(True), class_="ma-4")
        component()
    return main


app = API()
