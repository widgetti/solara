from solara.kitchensink import react, sol

title = "Fruit home"


@react.component
def Page():
    return sol.Success("Yay")
