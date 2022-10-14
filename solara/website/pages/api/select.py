"""
# Select components

Select are in two flavours, for single, and for multiple selections.


"""
import solara
from solara.website.utils import apidoc


@solara.component
def Page():
    with solara.VBox() as main:
        with solara.Card("Single selection"):
            food, set_food = solara.use_state("Banana")
            solara.Markdown(f"**Selected**: {food}")
            foods = ["Kiwi", "Banana", "Apple"]
            solara.Select(label="Food", value=food, values=foods, on_value=set_food)

        with solara.Card("Multiple selections"):
            all_languages = "Python C++ Java JavaScript TypeScript BASIC".split()
            languages, set_languages = solara.use_state([all_languages[0]])
            solara.Markdown(f"**Selected**: {languages}")
            solara.SelectMultiple("Languages", languages, all_languages, on_value=set_languages)

    return main


__doc__ += "# Select"
__doc__ += apidoc(solara.Select.f)  # type: ignore
__doc__ += "# SelectMultiple"
__doc__ += apidoc(solara.SelectMultiple.f)  # type: ignore
