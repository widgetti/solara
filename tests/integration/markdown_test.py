# tests all pages in the api docs
from pathlib import Path

import playwright.sync_api

from solara.alias import react, sol

HERE = Path(__file__).parent


md = """

# Solara markdown

```solara
import react_ipywidgets as react

import solara as sol


@react.component
def ClickButton():
    clicks, set_clicks = react.use_state(0)
    def on_click():
        set_clicks(clicks + 1)
        print("clicks", clicks)

    return sol.Button(label=f"Clicked: {clicks}", on_click=on_click)


app = ClickButton()
```

"""


@react.component
def MarkdownApp():
    return sol.Markdown(md, unsafe_solara_execute=True)


@react.component
def MarkdownAppOff():
    return sol.Markdown(md, unsafe_solara_execute=False)


@react.component
def MarkdownItApp():
    return sol.MarkdownIt(md, unsafe_solara_execute=True)


@react.component
def MarkdownItAppOff():
    return sol.MarkdownIt(md, unsafe_solara_execute=False)


app = MarkdownApp()
app_no_execute = MarkdownAppOff()
app_it = MarkdownItApp()
app_it_no_execute = MarkdownItAppOff()


def test_markdown(page: playwright.sync_api.Page, solara_server, solara_app, extra_include_path):
    with extra_include_path(HERE), solara_app("markdown_test:app"):
        page.goto(solara_server.base_url)
        page.locator("text=Clicked: 0").wait_for()
        page.locator("text=Clicked: 0").click()
        page.locator("text=Clicked: 1").wait_for()


def test_markdown_no_execute(page: playwright.sync_api.Page, solara_server, solara_app, extra_include_path):
    with extra_include_path(HERE), solara_app("markdown_test:app_no_execute"):
        page.goto(solara_server.base_url)
        page.locator("text=Solara execution is not enabled").wait_for()


def test_markdown_it(page: playwright.sync_api.Page, solara_server, solara_app, extra_include_path):
    with extra_include_path(HERE), solara_app("markdown_test:app_it"):
        page.goto(solara_server.base_url)
        page.locator("text=Clicked: 0").wait_for()
        page.locator("text=Clicked: 0").click()
        page.locator("text=Clicked: 1").wait_for()


def test_markdown_it_no_execute(page: playwright.sync_api.Page, solara_server, solara_app, extra_include_path):
    with extra_include_path(HERE), solara_app("markdown_test:app_it_no_execute"):
        page.goto(solara_server.base_url)
        page.locator("text=Solara execution is not enabled").wait_for()
