import solara

github_url = solara.util.github_url(__file__)

# list of nice soft colors
colors = [
    "#e6194b",
    "#3cb44b",
    "#ffe119",
    "#4363d8",
    "#f58231",
    "#911eb4",
]


@solara.component
def Page1():
    with solara.Sidebar():
        solara.Button(label="View source", icon_name="mdi-github-circle", attributes={"href": github_url, "target": "_blank"}, text=True, outlined=True)
        solara.Markdown("The sidebar will get scrollbars automatically, independently of the main content.")
        for i in range(10):
            with solara.Card(f"Card {i}"):
                solara.Info(f"Text {i}", color=colors[i % len(colors)])

    solara.Markdown("The main content will get scrollbars automatically, independently of the sidebar.")
    for i in range(10):
        with solara.Card(f"Card {i}"):
            solara.Info(f"Text {i}", color=colors[i % len(colors)])


@solara.component
def Page2():
    # it is important we do not interrupt the height 100% chain
    limit_content_height = solara.use_reactive(True)
    # warning: if we add "margin": "10px" to the style, we will trigger
    # scrollbars in the parent div, if you really need to add margins,
    # you should correct for that in the height using "calc(100% - 20px)"
    with solara.Column(style={"height": "100%"}):
        with solara.Sidebar():
            solara.Button(label="View source", icon_name="mdi-github-circle", attributes={"href": github_url, "target": "_blank"}, text=True, outlined=True)
            solara.Markdown("Main content columns will scroll together, or independently if we limit height to 100%")
            solara.Checkbox(label="Limit content height", value=limit_content_height)

        # if we do not limit height to 100%, solara's AppLayout will add a scroll bar
        # to the main content, which will be independent of the sidebar's scroll bar
        # but both columns will scroll together
        with solara.Columns([2, 4], style={"height": "100%"} if limit_content_height.value else {}):
            with solara.Card("I have my own scroll bar"):
                solara.Markdown("")
                for i in range(10):
                    with solara.Card(f"Card {i}"):
                        solara.Info(f"Text {i}", color=colors[i % len(colors)])
            with solara.Card("I also have my own scroll bar"):
                solara.Markdown("")
                for i in range(20):
                    with solara.Card(f"Card {i}"):
                        solara.Info(f"Text {i}", color=colors[i % len(colors)])


routes = [
    solara.Route(path="/", component=Page1, label="Scrolling"),
    solara.Route(path="custom", component=Page2, label="Custom scrolling"),
]
