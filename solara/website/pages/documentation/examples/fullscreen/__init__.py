"""Apps that run fullscreen"""
import solara

redirect = None


@solara.component
def Page():
    return solara.Markdown("Should not see me")
