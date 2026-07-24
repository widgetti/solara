import solara

clicks = solara.reactive(0)


@solara.component
def Page():
    solara.Button(label=f"Clicked: {clicks.value}", on_click=lambda: clicks.set(clicks.value + 1))
