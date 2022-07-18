import react_ipywidgets as react

import solara as sol


@react.component
def Page():
    clicks, set_clicks = react.use_state(0)

    color = "green"
    if clicks >= 5:
        color = "red"

    def on_click():
        set_clicks(clicks + 1)
        print("clicks", clicks)  # noqa

    return sol.Button(label=f"Clicked: {clicks}", on_click=on_click, color=color)
