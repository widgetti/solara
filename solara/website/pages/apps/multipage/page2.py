import solara

github_url = solara.util.github_url(__file__)


@solara.component
def Page():
    solara.Title("Page 2 set with title")
    with solara.Card("Page 2"):
        solara.Markdown("Page 2 is even better, even though it has no sidebar.")
        solara.Button(label="View source", icon_name="mdi-github-circle", attributes={"href": github_url, "target": "_blank"}, text=True, outlined=True)
