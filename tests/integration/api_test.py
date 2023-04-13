# tests pages in the api docs
import playwright.sync_api
from playwright.sync_api import expect

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


def test_api_style(page_session: playwright.sync_api.Page, solara_server, solara_app):
    with solara_app("solara.website.pages"):
        page_session.goto(solara_server.base_url + "/api/style")
        page_session.locator("text=Add a custom piece of CSS").first.wait_for()
        expect(page_session.locator(".mybutton")).to_have_css("color", "rgb(76, 175, 80)")

        # disable css
        page_session.locator('_vue=v-checkbox[label="Use CSS"]').click()
        expect(page_session.locator(".mybutton")).to_have_css("color", "rgba(0, 0, 0, 0.87)")

        # enable css again
        page_session.locator('_vue=v-checkbox[label="Use CSS"]').click()
        expect(page_session.locator(".mybutton")).to_have_css("color", "rgb(76, 175, 80)")


def test_api_cross_filter_select(page_session: playwright.sync_api.Page, solara_server, solara_app):
    with solara_app("solara.website.pages"):
        page_session.goto(solara_server.base_url + "/api/cross_filter_select")
        page_session.locator("text=244").wait_for()
        select_sex = page_session.locator('_vue=v-autocomplete[label="Select values in sex having values:"]')
        select_sex.click()
        page_session.locator("text=Female").click()
        page_session.locator("text=87 / 244").wait_for()


def test_dataframe(page_session: playwright.sync_api.Page, solara_server, solara_app):
    with solara_app("solara.website.pages"):
        page_session.goto(solara_server.base_url + "/api/dataframe")
        datatable_value_counts = page_session.locator(".solara-data-table").nth(1)
        datatable_value_counts.wait_for()

        # open the species hover menu
        datatable_value_counts.locator("th >> text=species_id >> _vue=v-icon").hover()
        page_session.locator("text=Value counts for species_id").wait_for()
        page_session.locator("text=Name: count").wait_for()

        # open the petal_width hover menu
        datatable_value_counts.locator("th >> text=petal_width >> _vue=v-icon").hover()
        page_session.locator("text=Name species").wait_for(state="detached")
        page_session.locator("text=Value counts for petal_width").wait_for()
        page_session.locator("text=Name: count").wait_for()
