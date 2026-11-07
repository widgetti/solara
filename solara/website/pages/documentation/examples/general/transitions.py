# check out https://solara.dev/ for documentation
# or https://github.com/widgetti/solara/
# And check out https://py.cafe/maartenbreddels for more examples

import solara
import solara.lab


clicks = solara.reactive(0)


@solara.component
def Page():
    color = "green"
    if clicks.value >= 5:
        color = "red"

    def increment():
        clicks.value += 1

    solara.Button(label=f"Clicked: {clicks}", on_click=increment, color=color)

    with solara.lab.TransitionFlip("X", show_first=(clicks.value % 2) == 0, duration=0.2):
        with solara.Card("Even") as el1:
            solara.Text("This number is even")
        with solara.Card("Odd") as el2:
            solara.Text("This number is even")

    with solara.Card("List"):
        TodoItem("Write", True)
        TodoItem("Read", False)

    RemovableCard()
    RemovableCard()
    solara.v.use_event(el1, "click", lambda *_ignore: increment())
    solara.v.use_event(el2, "click", lambda *_ignore: increment())


@solara.component
def RemovableCard():
    show = solara.use_reactive(True)
    with solara.lab.TransitionSlide("X", show_first=show.value, duration=0.5, translate_leave="100px"):
        with solara.Card("Some report"):
            with solara.Column():
                solara.Text(
                    "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum."
                )
                solara.Markdown("*Close the card to see it animate away*")
            with solara.CardActions():
                solara.v.Spacer()
                solara.Button("Close", on_click=lambda: show.set(False), text=True)


@solara.component
def TodoItem(text, default_value):
    done = solara.use_reactive(default_value)

    with solara.Row(style={"overflow": "hidden"}):
        solara.Switch(label=text, value=done)
        solara.v.Spacer()

        with solara.lab.TransitionSlide("X", show_first=done.value, duration=0.2):
            solara.v.Icon(children=["mdi-check"], color="success")
