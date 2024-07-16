import os
import playwright.sync_api

TEST_PORT = int(os.environ.get("PORT", "18765"))


def test_pyinstaller_basics(page: playwright.sync_api.Page):
    page.goto(f"http://localhost:{TEST_PORT}")
    page.locator("text=Clicked: 0").click()
    page.locator("text=Clicked: 1").wait_for()
