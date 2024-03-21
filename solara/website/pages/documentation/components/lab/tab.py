"""
# Tab

"""
import solara
import solara.lab
from solara.website.utils import apidoc

disabled = solara.reactive(False)
icon = solara.reactive(True)


@solara.component
def Page():
    solara.Checkbox(label="Disable Tab 2", value=disabled)
    solara.Checkbox(label="Show icon", value=icon)
    with solara.lab.Tabs():
        with solara.lab.Tab("Tab 1"):
            solara.Markdown("Hello")
        with solara.lab.Tab("Tab 2", disabled=disabled.value, icon_name="mdi-home" if icon.value else None):
            solara.Markdown("World")


__doc__ += apidoc(solara.lab.Tab.f)  # type: ignore
