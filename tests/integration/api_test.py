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


def test_api_markdown_editor(page: playwright.sync_api.Page, solara_server, solara_app):
    with solara_app("solara.website.pages"):
        page.goto(solara_server.base_url + "/documentation/components/")
        page.locator(".v-card >> text=Markdown Editor").first.click()
        page.locator('h1:has-text("Large heading")').wait_for()


def test_api_file_browser(page: playwright.sync_api.Page, solara_server, solara_app):
    with solara_app("solara.website.pages"):
        page.goto(solara_server.base_url + "/documentation/components/")
        page.locator(".v-card >> text=File Browser").first.click()
        page.locator("text=You are in directory").wait_for()


def test_api_matplotlib(page: playwright.sync_api.Page, solara_server, solara_app):
    with solara_app("solara.website.pages"):
        page.goto(solara_server.base_url + "/documentation/components/viz/matplotlib")
        page.locator("text=Arguments").first.wait_for()


def test_api_style(page: playwright.sync_api.Page, solara_server, solara_app):
    with solara_app("solara.website.pages"):
        page.goto(solara_server.base_url + "/documentation/components/advanced/style")
        page.locator("text=Add a custom piece of CSS").first.wait_for()
        expect(page.locator(".mybutton")).to_have_css("color", "rgb(76, 175, 80)")

        # disable css
        page.get_by_role("checkbox", name="Use CSS").click()
        expect(page.locator(".mybutton")).to_have_css("color", "rgba(0, 0, 0, 0.87)")

        # enable css again
        page.get_by_role("checkbox", name="Use CSS").click()
        expect(page.locator(".mybutton")).to_have_css("color", "rgb(76, 175, 80)")


def test_api_cross_filter_select(page: playwright.sync_api.Page, solara_server, solara_app):
    with solara_app("solara.website.pages"):
        page.goto(solara_server.base_url + "/documentation/api/cross_filter/cross_filter_select")
        page.locator("text=244").wait_for()
        page.locator("#loader-container").wait_for(state="hidden")
        select_sex = page.locator(".v-autocomplete", has_text="Select values in sex having values:")
        select_sex.get_by_label("Open").click()
        page.locator("text=Female").click()
        page.locator("text=87 / 244").wait_for()


def test_dataframe(page: playwright.sync_api.Page, solara_server, solara_app):
    with solara_app("solara.website.pages"):
        page.goto(solara_server.base_url + "/documentation/components/data/dataframe")
        datatable_value_counts = page.locator(".solara-data-table").nth(1)
        datatable_value_counts.wait_for()

        # scroll and wait for stability of test
        species_menu = datatable_value_counts.locator("th", has_text="species_id").locator(".solara-data-table-menu")
        species_menu.wait_for()
        species_menu.scroll_into_view_if_needed()
        page.wait_for_timeout(1000)

        # open the species hover menu
        species_menu.hover()
        page.locator("text=Value counts for species_id").wait_for()
        page.locator("text=Name: count").wait_for()

        # open the petal_width hover menu
        datatable_value_counts.locator("th", has_text="petal_width").locator(".solara-data-table-menu").hover()
        page.locator("text=Name species").wait_for(state="detached")
        page.locator("text=Value counts for petal_width").wait_for()
        page.locator("text=Name: count").wait_for()
