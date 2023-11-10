import solara

from . import SharedComponent

github_url = solara.util.github_url(__file__)


@solara.component
def Sub():
    with solara.Card("Sub component", margin=0, classes=["my-2"]):
        solara.Markdown("This sub component is the best")
        with solara.Sidebar():
            with solara.Card("Sidebar of sub component", margin=0, elevation=0):
                solara.Markdown("*Markdown* **is** 👍")
            SharedComponent()


@solara.component
def Page():
    with solara.Sidebar():
        with solara.Card("Sidebar of page 1", margin=0, elevation=0):
            solara.Markdown("Hi there 👋!")
            solara.Button(label="View source", icon_name="mdi-github-circle", attributes={"href": github_url, "target": "_blank"}, text=True, outlined=True)
    with solara.Card("Page 1"):
        Sub()
        solara.Markdown("Page 1 is the best")
