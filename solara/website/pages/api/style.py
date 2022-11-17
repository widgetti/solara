"""
# Style

"""
import solara
from solara.website.utils import apidoc


@solara.component
def Page():
    insert_css, set_insert_css = solara.use_state(True)

    css = """
    .mybutton {
        font-family: Serif;
    }

    /* this selector has to be very specific to override the vuetify style */
    .v-btn.mybutton {
        color: #4CAF50; /* Green */
    }
    /* vuetify's background color css has very high CSS-specificity, so we use !important */
    .mybutton {
        background-color: #FF9800 !important; /* Orange */
    }
    """

    with solara.VBox() as main:
        solara.Checkbox(label="Use CSS", value=insert_css, on_value=set_insert_css)
        solara.Markdown(
            f"""
## CSS Example that styles the button below
```css
{css}
```
"""
        )
        if insert_css:
            solara.Style(css)
        solara.Button(label="Advanced users might want to style this", icon_name="mdi-thumb-up", classes=["mybutton"])
    return main


__doc__ += apidoc(solara.Style.f)  # type: ignore
