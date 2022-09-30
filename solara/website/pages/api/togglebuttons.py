"""
# ToggleButtons

ToggleButtons are in two flavours, for single, and for multiple selections.


"""
import solara


@solara.component
def Page():
    with solara.VBox() as main:
        with solara.Card("Single selection"):
            food, set_food = solara.use_state("banana")
            solara.Markdown(f"**Selected**: {food}")
            with solara.ToggleButtonsSingle(food, on_value=set_food):
                solara.Button("Kiwi")
                solara.Button("Banana", value="banana")  # override the default value (the button label)
                solara.Button("Apple")

        with solara.Card("Multiple selections"):
            all_languages = "Python C++ Java JavaScript TypeScript BASIC".split()
            languages, set_languages = solara.use_state([all_languages[0]])
            solara.Markdown(f"**Selected**: {languages}")
            with solara.ToggleButtonsMultiple(languages, on_value=set_languages):
                for language in all_languages:
                    solara.Button(language, value=language)

    return main
