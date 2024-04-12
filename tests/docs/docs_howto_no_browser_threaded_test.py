import solara
import solara.lab
import ipyvuetify as v
import time


def test_docs_no_browser_api_thread():
    clicks = solara.reactive(0)

    @solara.component
    def ClickButton():
        @solara.lab.task
        def increment():
            # now we will wait for 0.3 seconds before updating the UI
            time.sleep(0.3)
            clicks.value += 1

        with solara.Card("Button in a card"):
            with solara.Column():
                solara.Button(label=f"Clicked: {clicks}", on_click=increment)

    # rc is short for render context
    box, rc = solara.render(ClickButton(), handle_error=False)
    finder = rc.find(v.Btn)
    button = finder.widget
    finder.assert_single()
    finder.assert_not_empty()
    assert button.children[0] == "Clicked: 0"

    # clicking will now start a thread, so we have to wait/poll for the UI to update
    button.click()

    button_after_delayed_click = rc.find(v.Btn, children=["Clicked: 1"])
    button_after_delayed_click.wait_for(timeout=2.5)
