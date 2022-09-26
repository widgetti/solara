from solara.alias import reacton, sol

title = "Fruit home"


@reacton.component
def Page():
    return sol.Success("Yay")
