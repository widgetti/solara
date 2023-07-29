import solara

from . import SharedComponent

github_url = solara.util.github_url(__file__)


@solara.component
def Page():
    component_state = solara.use_reactive(0)
    solara.Title("Page 2 set with title")
    with solara.Card("Page 2"):
        solara.Markdown("Page 2 is even better, even though it has no sidebar.")
        solara.Button(label="View source", icon_name="mdi-github-circle", attributes={"href": github_url, "target": "_blank"}, text=True, outlined=True)
        SharedComponent()

        with solara.Card("Shown only on page2", style={"max-width": "500px"}, margin=0, classes=["my-2"]):
            solara.Markdown(
                f"""
                The lifetime of `component_state` if bound to this page. If you navigate away from it,
                the state will be reset.

                It creates the `component_state` [using the use_reactive hook](https://solara.dev/api/use_reactive)
                so that the state is bound to the component.

                See also [about state management](https://solara.dev/docs/fundamentals/state-management) for more information.


                component_state: {component_state.value}
                """
            )
            solara.Button(
                label="Increment component_state", icon_name="mdi-plus", on_click=lambda: component_state.set(component_state.value + 1), outlined=True
            )
