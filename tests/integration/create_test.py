import os

import playwright.sync_api

from solara.util import cwd


def test_create_button(page: playwright.sync_api.Page, solara_server, solara_app, tmpdir):
    script = tmpdir / "button.py"
    assert os.system(f"solara create button {script}") == 0
    with solara_app(str(script)):
        page.goto(solara_server.base_url)
        page.locator("text=Clicked: 0").click()
        page.locator("text=Clicked: 1").click()


def test_create_markdown(page: playwright.sync_api.Page, solara_server, solara_app, tmpdir):
    script = tmpdir / "button.py"
    assert os.system(f"solara create markdown {script}") == 0
    with solara_app(str(script)):
        page.goto(solara_server.base_url)
        page.locator("text=Renders like").wait_for()


def test_create_portal(page: playwright.sync_api.Page, solara_server, solara_app, tmpdir):
    package_dir = tmpdir / "solara-portal-pytest"
    assert os.system(f"solara create portal {package_dir}") == 0
    with cwd(package_dir):
        assert os.system("pip install .") == 0
    with solara_app("solara_portal_pytest.pages"):
        page.goto(solara_server.base_url)
        page.locator("text=Scatter for titanic").wait_for()
        page.locator("text=Open table view").first.click()
        page.locator("text=pclass").wait_for()
        page.go_back()
        page.locator("text=Read article").first.click()
        page.locator("text=Substiterat vati").first.wait_for()
        page.go_back()
        page.locator("text=Scatter for titanic").wait_for()
        page.wait_for_timeout(100)
        page.locator("text=Scatter for titanic").click()
        page.locator("text=x").first.wait_for()
