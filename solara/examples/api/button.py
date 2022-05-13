"""
# Button
A button that can be clicked to trigger an event.
"""
from solara.kitchensink import react, sol


@react.component
def ButtonDemo():
    count, set_count = react.use_state(0)

    def increment():
        set_count(count + 1)

    with sol.VBox() as main:
        with sol.HBox():
            sol.Button(label=f"Clicked {count} times", on_click=increment, icon_name="mdi-thumb-up")
    return main


Component = sol.Button
App = ButtonDemo
