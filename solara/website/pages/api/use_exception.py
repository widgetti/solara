import solara

title = "use_exception"
set_fail = None
clear = None


@solara.component
def UnstableComponent(number: int):
    if number == 3:
        raise Exception("I do not like 3")
    return solara.Text(f"You picked {number}")


@solara.component
def Page():
    value, set_value = solara.use_state(1)
    value_previous = solara.use_previous(value)
    exception, clear_exception = solara.use_exception()
    # print(exception)
    with solara.VBox() as main:
        if exception:

            def reset():
                set_value(value_previous)
                clear_exception()

            solara.Text("Exception: " + str(exception))
            solara.Button(label="Go to previous state", on_click=reset)
        else:
            solara.IntSlider(value=value, min=0, max=10, on_value=set_value, label="Pick a number, except 3")
            UnstableComponent(value)
    return main
