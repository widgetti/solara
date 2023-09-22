import pytest
from playwright.sync_api import Page, expect

# Tests are only run in solara, since others don't support parametrization.


# Tests rendering of menus, as well as click functionality on child element
@pytest.mark.parametrize("test_type", ["Menu", "ClickMenu", "ContextMenu"])
def test_menus_playwright(test_type, solara_test, page_session: Page, assert_solara_snapshot):
    import solara
    from solara.lab import ClickMenu, ContextMenu, Menu

    @solara.component
    def Page():
        # without height dropdown menu won't be visible in screenshots
        with solara.Column(classes=["test-class-container"], style="height:300px; width: 400px;"):
            text = solara.use_reactive("pre-test")

            def on_click():
                text.set("Works!")

            solara.Text(text.value, classes=["test-class-text"])

            menu_activator = solara.Button("activator")
            menu_child = solara.Button("child", on_click=on_click, classes=["test-class-child"])

            if test_type == "Menu":
                Menu(activator=menu_activator, children=[menu_child])
            elif test_type == "ClickMenu":
                ClickMenu(activator=menu_activator, children=[menu_child])
            else:
                ContextMenu(activator=menu_activator, children=[menu_child])

    solara.display(Page())

    text_el = page_session.locator(".test-class-text")
    expect(text_el).to_contain_text("pre-test")
    activator_button = page_session.locator("text=activator")
    expect(page_session.locator(".test-class-child")).to_have_count(0)
    if test_type == "ContextMenu":
        activator_button.click(button="right")
    else:
        activator_button.click()

    child_button = page_session.locator("text=child")
    page_session.wait_for_timeout(350)  # Wait for any animations after click
    expect(page_session.locator(".test-class-child")).to_be_visible()
    child_button.click()
    page_session.wait_for_timeout(350)
    expect(text_el).to_contain_text("Works!")


# Tests successive click behaviour of menus
@pytest.mark.parametrize("test_type", ["Menu", "ClickMenu", "ContextMenu"])
def test_menus_successive(test_type, solara_test, page_session: Page):
    import solara
    from solara.lab import ClickMenu, ContextMenu, Menu

    @solara.component
    def Page():
        menu_activator = solara.Div(style="height: 200px; width: 400px;", classes=["test-class-activator"])
        menu_child = solara.Div(classes=["test-class-menu"], style="height: 100px; width: 50px;")

        if test_type == "Menu":
            Menu(activator=menu_activator, children=[menu_child])
        elif test_type == "ClickMenu":
            ClickMenu(activator=menu_activator, children=[menu_child])
        else:
            ContextMenu(activator=menu_activator, children=[menu_child])

    solara.display(Page())

    activator_el = page_session.locator(".test-class-activator")
    expect(page_session.locator(".test-class-menu")).to_have_count(0)  # Menu should not exist yet
    if test_type == "ContextMenu":
        activator_el.click(button="right")
    else:
        activator_el.click()

    page_session.wait_for_timeout(350)  # Wait for any animations after click
    expect(page_session.locator(".test-class-menu")).to_be_in_viewport()  # Menu should be visible now

    if test_type == "ContextMenu":
        activator_el.click(button="right")
        page_session.wait_for_timeout(350)
        expect(page_session.locator(".test-class-menu")).to_be_in_viewport()
    else:
        activator_el.click()
        page_session.wait_for_timeout(350)
        expect(page_session.locator(".test-class-menu")).not_to_be_in_viewport()  # After second click, Menu and ClickMenu should disappear
