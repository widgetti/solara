import os

import playwright.sync_api

# from solara.util import cwd


def test_create_button(page_session: playwright.sync_api.Page, solara_server, solara_app, tmpdir):
    script = tmpdir / "button.py"
    assert os.system(f"solara create button {script}") == 0
    with solara_app(str(script)):
        page_session.goto(solara_server.base_url)
        page_session.locator("text=Clicked: 0").click()
        page_session.locator("text=Clicked: 1").click()


def test_create_markdown(page_session: playwright.sync_api.Page, solara_server, solara_app, tmpdir):
    script = tmpdir / "button.py"
    assert os.system(f"solara create markdown {script}") == 0
    with solara_app(str(script)):
        page_session.goto(solara_server.base_url)
        page_session.locator("text=Renders like").wait_for()


# def test_create_portal(page_session: playwright.sync_api.Page, solara_server, solara_app, tmpdir):
#     package_dir = tmpdir / "solara-portal-pytest"
#     assert os.system(f"solara create portal {package_dir}") == 0
#     with cwd(package_dir):
#         assert os.system("pip install .") == 0
#     with solara_app("solara_portal_pytest.pages"):
#         page_session.goto(solara_server.base_url)
#         page_session.locator("text=Scatter for titanic").wait_for()
#         page_session.locator("text=Open table view").first.click()
#         page_session.locator("text=pclass").wait_for()
#         page_session.go_back()
#         page_session.locator("text=Read article").first.click()
#         page_session.locator("text=Substiterat vati").first.wait_for()
#         page_session.go_back()
#         page_session.locator("text=Scatter for titanic").wait_for()
#         page_session.wait_for_timeout(100)
#         page_session.locator("text=Scatter for titanic").click()
#         page_session.locator("text=x").first.wait_for()
