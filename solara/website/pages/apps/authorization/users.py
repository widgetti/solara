import solara

from . import user

github_url = solara.util.github_url(__file__)


@solara.component
def Page():
    assert user.value is not None
    solara.Markdown(f"Hi {user.value.username}!")
    solara.Button(label="View source", icon_name="mdi-github-circle", attributes={"href": github_url, "target": "_blank"}, text=True, outlined=True)
