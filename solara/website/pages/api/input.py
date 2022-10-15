"""# Input fields

This page contains all the input fields available in Solara.



"""
import solara
from solara.website.utils import apidoc


@solara.component
def Page():
    text, set_text = solara.use_state("Hello world")

    with solara.VBox() as main:
        solara.InputText("Enter some text", value=text, on_value=set_text)
        with solara.HBox():
            solara.Button("Clear", on_click=lambda: set_text(""))
            solara.Button("Reset", on_click=lambda: set_text("Hello world"))
        solara.Markdown(f"**You entered**: {text}")

    return main


__doc__ += apidoc(solara.InputText.f)  # type: ignore
