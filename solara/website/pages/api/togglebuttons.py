"""
# ToggleButtons

ToggleButtons are in two flavours, for single, and for multiple selections.


"""
import solara
from solara.website.utils import apidoc


@solara.component
def Page():
    with solara.VBox() as main:
        with solara.Card("Single selection"):
            food, set_food = solara.use_state("Banana")
            solara.Markdown(f"**Selected**: {food}")
            solara.ToggleButtonsSingle(food, values=["Kiwi", "Banana", "Apple"], on_value=set_food)

        with solara.Card("Multiple selections"):
            all_languages = "Python C++ Java JavaScript TypeScript BASIC".split()
            languages, set_languages = solara.use_state([all_languages[0]])
            solara.Markdown(f"**Selected**: {languages}")
            solara.ToggleButtonsMultiple(languages, values=all_languages, on_value=set_languages)

        with solara.Card("Custom buttons"):
            direction, set_direction = solara.use_state("left")
            solara.Markdown(f"**Selected**: {direction}")
            # instead of using the values argument, we can use the buttons as children
            # the label of the button will be used as value, if no value is given.
            with solara.ToggleButtonsSingle(direction, on_value=set_direction):
                # note that the label and the value are different
                solara.Button("Up", icon_name="mdi-arrow-up-bold", value="up", text=True)
                solara.Button("Down", icon_name="mdi-arrow-down-bold", value="down", text=True)
                solara.Button("Left", icon_name="mdi-arrow-left-bold", value="left", text=True)
                solara.Button("Right", icon_name="mdi-arrow-right-bold", value="right", text=True)

    return main


__doc__ += "# ToggleButtonsSingle"
__doc__ += apidoc(solara.ToggleButtonsSingle.f)  # type: ignore
__doc__ += "# ToggleButtonsMultiple"
__doc__ += apidoc(solara.ToggleButtonsMultiple.f)  # type: ignore
