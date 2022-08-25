from solara.kitchensink import react, sol

set_fail = None
clear = None


@react.component
def UnstableComponent(number: int):
    if number == 3:
        raise Exception("I do not like 3")
    return sol.Text(f"You picked {number}")


@react.component
def Page():
    value, set_value = react.use_state(1)
    value_previous = sol.use_previous(value)
    exception, clear_exception = react.use_exception()
    # print(exception)
    with sol.VBox() as main:
        if exception:

            def reset():
                set_value(value_previous)
                clear_exception()

            sol.Text("Exception: " + str(exception))
            sol.Button(label="Go to previous state", on_click=reset)
        else:
            sol.IntSlider(value=value, min=0, max=10, on_value=set_value, label="Pick a number, except 3")
            UnstableComponent(value)
    return main
