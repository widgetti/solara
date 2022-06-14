"""
# use_state_or_update

Like `react.use_state`, except it will update the value if the input value changes.

This is useful to give a component state *or* allow the state to be controlled by the parent component


"""
from solara.kitchensink import react, sol


@react.component
def SliderWithoutState(value: int):
    # Note that this is very bad practive, if value is an input change and the slider
    # can change it, this component should have a on_value callback to allow the parent
    # component to manage its state.
    # This component is only for demoing/understanding.
    return sol.IntSlider("value", value=value)


@react.component
def SliderWithState(value: int):
    # effectively, because of use_state, the value prop passed in is
    # only a default value.
    value, set_value = react.use_state(value)
    return sol.IntSlider("value", value=value, on_value=set_value)


@react.component
def SliderWithStateOrUpdate(value: int):
    value, set_value = sol.use_state_or_update(value)
    return sol.IntSlider("value", value=value, on_value=set_value)


@react.component
def Test():
    parent_value, set_parent_value = react.use_state(4)
    # used to force rerenders
    rerender_counter, set_rerender_counter = react.use_state(4)
    with sol.VBox() as main:
        with sol.Card("Parent value selection"):
            sol.Info("This slider value gets passed down to the child components")
            sol.IntSlider("parent value", value=parent_value, on_value=set_parent_value)
            sol.Button("Force redraw", on_click=lambda: set_rerender_counter(rerender_counter + 1))

        with sol.Card("Child without state"):
            sol.Info("This child will simply render the value passed into the argument, a redraw will reset it to its parent value.")
            SliderWithoutState(parent_value)

        with sol.Card("Child with state"):
            sol.Info("This child will not care about the value passed into the prop, it manages its own state.")
            SliderWithState(parent_value)

        with sol.Card("Child with state (or update)"):
            sol.Info("This child will update when the passes in a new value, but a redraw will not reset it.")
            SliderWithStateOrUpdate(parent_value)

        with sol.Card("Child with state + key"):
            sol.Info(
                "We can also use the `.key(...)` method to force the component to forget its state, this will however cause the widget to be re-created"
                "(a performance penalty)."
            )
            SliderWithState(parent_value).key(f"slider-{parent_value}")

    return main


App = Test
app = App()
