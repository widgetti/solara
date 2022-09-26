from solara.alias import reacton, sol


@reacton.component
def Layout(children=[]):
    with sol.VBox(children=children) as main:
        sol.Info("Footer")
    return main
