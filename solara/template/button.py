import reacton

import solara as sol


@reacton.component
def Page():
    clicks, set_clicks = reacton.use_state(0)

    color = "green"
    if clicks >= 5:
        color = "red"

    def on_click():
        set_clicks(clicks + 1)
        print("clicks", clicks)  # noqa

    return sol.Button(label=f"Clicked: {clicks}", on_click=on_click, color=color)
