import solara


@solara.component
def Page():
    clicks, set_clicks = solara.use_state(0)

    color = "green"
    if clicks >= 5:
        color = "red"

    def on_click():
        set_clicks(clicks + 1)
        print("clicks", clicks)  # noqa

    return solara.Button(label=f"Clicked: {clicks}", on_click=on_click, color=color)
