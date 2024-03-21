"""ipywidget library example"""
import solara

redirect = None


@solara.component
def Page():
    return solara.Markdown("Should not see me")
