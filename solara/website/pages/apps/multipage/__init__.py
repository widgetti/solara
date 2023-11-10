import solara

github_url = solara.util.github_url(__file__)
# some app state that outlives a single page
app_state = solara.reactive(0)


@solara.component
def SharedComponent():
    with solara.Card("Shown on each page", style={"max-width": "500px"}, margin=0, classes=["my-2"]):
        solara.Markdown(
            f"""
            This component will be used on each page.

            It uses the `app_state` [reactive variable](https://solara.dev/api/reactive)
            so that the state outlives each page


            app_state: {app_state.value}
            """
        )
        solara.Button(label="Increment app_state", icon_name="mdi-plus", on_click=lambda: app_state.set(app_state.value + 1), outlined=True)


@solara.component
def Page():
    with solara.Sidebar():
        solara.Markdown("This is the sidebar at the home page!")
    with solara.Card("Home"):
        solara.Markdown("This is the home page")
        solara.Button(label="View source", icon_name="mdi-github-circle", attributes={"href": github_url, "target": "_blank"}, text=True, outlined=True)

        SharedComponent()


@solara.component
def Layout(children):
    return solara.AppLayout(children=children)
