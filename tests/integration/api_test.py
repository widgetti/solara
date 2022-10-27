# tests pages in the api docs
import playwright.sync_api

# def test_api_sqlcode(page: playwright.sync_api.Page, solara_server, solara_app):
#     # with screenshot_on_error(page, 'tmp/test_docs_basics.png'):
#     with solara_app("solara.website.pages"):
#         page.goto(solara_server.base_url + "/api")
#         page.locator("text=Sql Code").click()
#         page.locator('button:has-text("Execute")').wait_for()


# def test_api_grid_draggable(page: playwright.sync_api.Page, solara_server, solara_app):
#     # with screenshot_on_error(page, 'tmp/test_docs_basics.png'):
#     with solara_app("solara..website.pages"):
#         page.goto(solara_server.base_url + "/api")
#         page.locator("text=GridDraggable").click()
#         page.locator('button:has-text("Reset to initial layout")').wait_for()


def test_api_markdown_editor(page_session: playwright.sync_api.Page, solara_server, solara_app):
    with solara_app("solara.website.pages"):
        page_session.goto(solara_server.base_url + "/api/")
        page_session.locator("text=Markdown Editor").first.click()
        page_session.locator('h1:has-text("Large heading")').wait_for()


def test_api_file_browser(page_session: playwright.sync_api.Page, solara_server, solara_app):
    with solara_app("solara.website.pages"):
        page_session.goto(solara_server.base_url + "/api/")
        page_session.locator("text=File Browser").first.click()
        page_session.locator("text=You are in directory").wait_for()


def test_api_matplotlib(page_session: playwright.sync_api.Page, solara_server, solara_app):
    with solara_app("solara.website.pages"):
        page_session.goto(solara_server.base_url + "/api/matplotlib")
        page_session.locator("text=Arguments").first.wait_for()
