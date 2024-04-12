import solara
import ipyvuetify as v


def test_docs_no_browser_api_find():
    clicks = solara.reactive(0)

    @solara.component
    def ClickButton():
        def increment():
            clicks.value += 1

        with solara.Card("Button in a card"):
            with solara.Column().meta(ref="somecolumn"):
                solara.Button(label=f"Clicked: {clicks}", on_click=increment)
            with solara.Column():
                solara.Button(label="Not the button we need")

    # rc is short for render context
    box, rc = solara.render(ClickButton(), handle_error=False)
    # this find will make the .widget fail, because it matches two buttons
    # finder = rc.find(v.Btn)
    # We can refine our search by adding constraints to attributes of the widget
    button_locator = rc.find(v.Btn, children=["Clicked: 0"])
    # basics asserts are supported, like assert_single(), assert_empty(), assert_not_empty()
    button_locator.assert_single()
    button = button_locator.widget
    # .find calls can also be nested, and can use the meta_ref to find the right widget
    # finder = rc.find(meta_ref="somecolumn").find(v.Btn)
    button.click()
    assert clicks.value == 1
    rc.find(v.Btn, children=["Clicked: 1"]).assert_single()
