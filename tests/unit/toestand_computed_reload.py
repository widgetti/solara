import solara
import solara.lab

value_reactive = solara.reactive(1.0)


@solara.lab.computed
def computed_reactive():
    return value_reactive.value + 1.0


@solara.component
def Page():
    solara.FloatSlider("test", value=value_reactive)
    solara.InputFloat("test", value=computed_reactive.value)
