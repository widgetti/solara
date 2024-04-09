import solara
import ipyvuetify as v


def test_docs_no_browser_simple():
    clicks = solara.reactive(0)

    @solara.component
    def ClickButton():
        def increment():
            clicks.value += 1

        solara.Button(label=f"Clicked: {clicks}", on_click=increment)

    # rc is short for render context
    box, rc = solara.render(ClickButton(), handle_error=False)
    button = box.children[0]
    assert isinstance(button, v.Btn)
    assert button.children[0] == "Clicked: 0"
    # trigger the click event handler without a browser
    button.click()
    assert clicks.value == 1
    assert button.children[0] == "Clicked: 1"
