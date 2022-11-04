"""# Input fields

This page contains all the input fields available in Solara.

# InputText
"""
import solara
from solara.website.utils import apidoc


@solara.component
def Page():
    text, set_text = solara.use_state("Hello world")
    password, set_password = solara.use_state("Super secret")
    number, set_number = solara.use_state(42.0)

    continuous_update, set_continuous_update = solara.use_state(False)

    with solara.VBox() as main:
        with solara.Card("Settings"):
            solara.Checkbox(label="Continuous update", value=continuous_update, on_value=set_continuous_update)

        with solara.Card("Text"):
            solara.InputText("Enter some text", value=text, on_value=set_text, continuous_update=continuous_update)
            with solara.HBox():
                solara.Button("Clear", on_click=lambda: set_text(""))
                solara.Button("Reset", on_click=lambda: set_text("Hello world"))
            solara.Markdown(f"**You entered**: {text}")

        with solara.Card("Password"):
            solara.InputText("Enter a password", value=password, on_value=set_password, password=True, continuous_update=continuous_update)
            with solara.HBox():
                solara.Button("Clear", on_click=lambda: set_password(""))
                solara.Button("Reset", on_click=lambda: set_password("Super secret"))
            solara.Markdown(f"**You entered**: {password}")

        with solara.Card("Number (float)"):
            solara.InputFloat("Enter some number", value=number, on_value=set_number, continuous_update=continuous_update)
            with solara.HBox():
                solara.Button("Reset", on_click=lambda: set_number(42))
            solara.Markdown(f"**You entered**: {number}")

    return main


__doc__ += apidoc(solara.InputText.f)  # type: ignore

__doc__ += "# InputFloat"
__doc__ += apidoc(solara.InputFloat.f)  # type: ignore
