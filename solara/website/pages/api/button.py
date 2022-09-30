"""
# Button
A button that can be clicked to trigger an event.
"""
import solara


@solara.component
def Page():
    count, set_count = solara.use_state(0)

    def increment():
        set_count(count + 1)

    with solara.VBox() as main:
        with solara.HBox():
            solara.Button(label=f"Clicked {count} times", on_click=increment, icon_name="mdi-thumb-up")
    return main
