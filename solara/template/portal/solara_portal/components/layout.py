from solara.alias import reacton, sol


@reacton.component
def Layout(children=[]):
    return sol.VBox(children=children)
