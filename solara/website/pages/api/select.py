"""
# Select

Select are in two flavours, for single, and for multiple selections.


"""
from solara.kitchensink import react, sol


@react.component
def Page():
    with sol.VBox() as main:
        with sol.Card("Single selection"):
            food, set_food = react.use_state("Banana")
            sol.Markdown(f"**Selected**: {food}")
            foods = ["Kiwi", "Banana", "Apple"]
            sol.Select(label="Food", value=food, values=foods, on_value=set_food)

        with sol.Card("Multiple selections"):
            all_languages = "Python C++ Java JavaScript TypeScript BASIC".split()
            languages, set_languages = react.use_state([all_languages[0]])
            sol.Markdown(f"**Selected**: {languages}")
            sol.SelectMultiple("Languages", languages, all_languages, on_value=set_languages)

    return main
