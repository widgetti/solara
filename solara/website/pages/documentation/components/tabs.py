"""
# Tabs

"""
import solara
import solara.lab
from solara.website.utils import apidoc

disabled = solara.reactive(False)
align = solara.reactive("center")
grow = solara.reactive(False)
vertical = solara.reactive(False)
dark = solara.reactive(False)


@solara.component
def Page():
    with solara.Card("Controls"):
        with solara.Row():
            solara.Checkbox(label="Grow", value=grow)
            solara.Checkbox(label="Vertical", value=vertical)
            solara.Checkbox(label="Dark", value=dark)
        if vertical.value:
            align.value = "start"
        else:
            if not grow.value:
                with solara.Row(style={"align-items": "center"}):
                    solara.Text("Align:")
                    solara.ToggleButtonsSingle(value=align, values=["start", "center", "end"], dense=True)
    with solara.lab.Tabs(
        vertical=vertical.value,
        grow=grow.value,
        align=align.value,
        dark=dark.value,
        background_color="primary" if dark.value else None,
        slider_color="secondary" if dark.value else None,
    ):
        with solara.lab.Tab("Tab 1"):
            solara.Markdown("Hello")
        with solara.lab.Tab("Tab 2"):
            solara.Markdown("World")


__doc__ += apidoc(solara.lab.Tabs.f)  # type: ignore
