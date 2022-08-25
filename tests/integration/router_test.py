import playwright
import playwright.sync_api


def test_docs_basics(page: playwright.sync_api.Page, solara_server, solara_app):
    # with screenshot_on_error(page, 'tmp/test_docs_basics.png'):
    with solara_app("solara.website.pages"):
        # page.goto(solara_server.base_url)
        # assert page.title() == "Hello from Solara ☀️"
        # page.locator('div[role="tab"]:has-text("Demo")').click()
        page.goto(solara_server.base_url + "/api/use_route/fruit/banana")
        page.locator("text=You chose banana").wait_for()
        page.locator('button:has-text("kiwi")').click()
        page.locator("text=You chose kiwi").wait_for()
        page.locator('button:has-text("apple")').click()
        page.locator("text=You chose apple").wait_for()
        # back to kiwi
        page.go_back()
        page.locator("text=You chose kiwi").wait_for()
        # back to banana
        page.go_back()
        page.locator("text=You chose banana").wait_for()

        # forward to kiwi
        page.go_forward()
        page.locator("text=You chose kiwi").wait_for()

        # go to wrong fruit
        page.locator('button:has-text("wrong fruit")').click()

        # and follow the fallback link
        page.locator("text=Fruit not found, go to banana").click()
        page.locator("text=You chose banana").wait_for()

        # another wrong link
        page.locator('button:has-text("wrong url")').click()
        page.locator("text=Page does not exist").wait_for()
