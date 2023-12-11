"""Large Language Models and Generative AI examples."""
import solara

title = "AI"
redirect = None


@solara.component
def Page():
    return solara.Markdown("Click an example on the left")
