import playwright
import playwright.sync_api


def test_landing(page_session: playwright.sync_api.Page, solara_server, solara_app):
    # with screenshot_on_error(page, 'tmp/test_docs_basics.png'):
    with solara_app("solara.website.pages"):
        page_session.goto(solara_server.base_url)
        page_session.locator("text=React-style web framework").wait_for()
        page_session.locator("text=API").first.click()
        page_session.locator("text=Matplotlib").first.wait_for()
        page_session.go_back()
        page_session.locator("text=React-style web framework").wait_for()


def test_docs_basics(page_session: playwright.sync_api.Page, solara_server, solara_app):
    # with screenshot_on_error(page, 'tmp/test_docs_basics.png'):
    with solara_app("solara.website.pages"):
        page_session.goto(solara_server.base_url + "/api/use_route/fruit/banana")
        page_session.locator("text=You chose banana").wait_for()
        page_session.locator('button:has-text("kiwi")').click()
        page_session.locator("text=You chose kiwi").wait_for()
        page_session.locator('button:has-text("apple")').click()
        page_session.locator("text=You chose apple").wait_for()
        # back to kiwi
        page_session.go_back()
        page_session.locator("text=You chose kiwi").wait_for()
        # back to banana
        page_session.go_back()
        page_session.locator("text=You chose banana").wait_for()

        # forward to kiwi
        page_session.go_forward()
        page_session.locator("text=You chose kiwi").wait_for()

        # go to wrong fruit
        page_session.locator('button:has-text("wrong fruit")').click()

        # and follow the fallback link
        page_session.locator("text=Fruit not found, go to banana").click()
        page_session.locator("text=You chose banana").wait_for()

        # another wrong link
        page_session.locator('button:has-text("wrong url")').click()
        page_session.locator("text=Page does not exist").wait_for()
