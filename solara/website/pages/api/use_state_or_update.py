"""
# use_state_or_update

Like `solara.use_state`, except it will update the value if the input value changes.

This is useful to give a component state *or* allow the state to be controlled by the parent component


"""
import solara

title = "use_state_or_update"


@solara.component
def SliderWithoutState(value: int):
    # Note that this is a very bad practice, if value is an input change and the slider
    # can change it, this component should have a on_value callback to allow the parent
    # component to manage its state.
    # This component is only for demoing/understanding.
    return solara.IntSlider("value", value=value)


@solara.component
def SliderWithState(value: int):
    # effectively, because of use_state, the value prop passed in is
    # only a default value.
    value, set_value = solara.use_state(value)
    return solara.IntSlider("value", value=value, on_value=set_value)


@solara.component
def SliderWithStateOrUpdate(value: int):
    value, set_value = solara.use_state_or_update(value)
    return solara.IntSlider("value", value=value, on_value=set_value)


@solara.component
def Page():
    parent_value, set_parent_value = solara.use_state(4)
    # used to force rerenders
    rerender_counter, set_rerender_counter = solara.use_state(4)
    with solara.VBox() as main:
        with solara.Card("Parent value selection"):
            solara.Info("This slider value gets passed down to the child components")
            solara.IntSlider("parent value", value=parent_value, on_value=set_parent_value)
            solara.Button("Force redraw", on_click=lambda: set_rerender_counter(rerender_counter + 1))

        with solara.Card("Child without state"):
            solara.Info("This child will simply render the value passed into the argument, a redraw will reset it to its parent value.")
            SliderWithoutState(parent_value)

        with solara.Card("Child with state"):
            solara.Info("This child will not care about the value passed into the prop, it manages its own state.")
            SliderWithState(parent_value)

        with solara.Card("Child with state (or update)"):
            solara.Info("This child will update when the passes in a new value, but a redraw will not reset it.")
            SliderWithStateOrUpdate(parent_value)

        with solara.Card("Child with state + key"):
            solara.Info(
                "We can also use the `.key(...)` method to force the component to forget its state, this will however cause the widget to be re-created"
                "(a performance penalty)."
            )
            SliderWithState(parent_value).key(f"slider-{parent_value}")

    return main
