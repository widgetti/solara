import threading
from pathlib import Path

import playwright
import playwright.sync_api
import reacton.ipywidgets as w

import solara

HERE = Path(__file__).parent


def test_large_cookie(browser: playwright.sync_api.Browser, page_session: playwright.sync_api.Page, solara_server, solara_app):
    with solara_app("solara.website.pages"):
        port = solara_server.port
        # more than 8kb of cookies
        for i in range(9):
            browser.contexts[0].add_cookies([{"name": f"a_{i}", "value": "a" * 1024, "url": f"http://localhost:{port}"}])
        page_session.goto(solara_server.base_url)
        page_session.locator("text=Examples").first.click()


def test_docs_basics(page_session: playwright.sync_api.Page, solara_server, solara_app):
    with solara_app("solara.website.pages"):
        page_session.goto(solara_server.base_url)
        page_session.locator("text=Examples").first.click()

        page_session.locator("text=Calculator").first.click()
        page_session.locator("text=+/-").wait_for()
        page_session.screenshot(path="tmp/screenshot_calculator.png")

        page_session.locator("text=Bqplot").first.click()
        page_session.locator("text=Exponent").wait_for()
        page_session.screenshot(path="tmp/screenshot_bqplot.png")

        page_session.locator("text=Scatter plot using Plotly").first.click()
        page_session.locator("text=plotly express").first.wait_for()
        page_session.screenshot(path="tmp/screenshot_plotly.png")

        page_session.locator("text=Plotly Image Annotator").first.click()
        page_session.locator("text=how to annotate images with").first.wait_for()


@solara.component
def ClickButton():
    count, set_count = solara.use_state(0)
    if not isinstance(count, int):
        print("oops, state issue?")  # noqa
        count = 0

    def on_click():
        set_count(count + 1)

    return solara.Button(f"Clicked: {count}", on_click=on_click)


@solara.component
def ThreadTest():
    label, set_label = solara.use_state("initial")
    use_thread, set_use_thread = solara.use_state(False)

    def from_thread():
        set_label("from thread")

    def start_thread():
        if use_thread:
            thread = threading.Thread(target=from_thread)
            thread.start()
            return thread.join

    solara.use_side_effect(start_thread, [use_thread])
    # we need to trigger creating a new widget, to make sure we
    # invoke a solara.server.app.get_current_context
    if label == "initial":
        return w.Button(description=label, on_click=lambda: set_use_thread(True))
    else:
        return w.Label(value=label)


def test_from_thread(page_session: playwright.sync_api.Page, solara_server, solara_app, extra_include_path):
    with extra_include_path(HERE), solara_app("server_test:ThreadTest"):
        page_session.goto(solara_server.base_url)
        el = page_session.locator(".jupyter-widgets")
        assert el.text_content() == "initial"
        page_session.wait_for_timeout(500)
        el.click()
        page_session.locator("text=from thread").wait_for()


def test_state(page_session: playwright.sync_api.Page, solara_server, solara_app, extra_include_path):
    with extra_include_path(HERE), solara_app("server_test:ClickButton"):
        page_session.goto(solara_server.base_url)
        page_session.locator("text=Clicked: 0").click()
        page_session.locator("text=Clicked: 1").click()
        # refresh...
        page_session.goto(solara_server.base_url)
        # and state should NOT be restored
        page_session.locator("text=Clicked: 0").wait_for()


def test_from_thread_two_users(browser: playwright.sync_api.Browser, solara_server, solara_app, extra_include_path):
    with extra_include_path(HERE), solara_app("server_test:ThreadTest"):
        context1 = browser.new_context()
        page1 = context1.new_page()
        context2 = browser.new_context()
        page2 = context2.new_page()

        page1.goto(solara_server.base_url)

        el1 = page1.locator(".jupyter-widgets")
        assert el1.text_content() == "initial"

        page2.goto(solara_server.base_url)
        el2 = page2.locator(".jupyter-widgets")
        assert el2.text_content() == "initial"

        page1.wait_for_timeout(500)
        page1.wait_for_timeout(500)

        el1.click()
        page1.locator("text=from thread").wait_for()

        page2.wait_for_timeout(500)
        assert el2.text_content() == "initial"

        el2.click()
        page2.locator("text=from thread").wait_for()
        page1.close()
        page2.close()


@solara.component
def StaticPage():
    return w.Label(value="Hello world")


def test_run_in_iframe(page_session: playwright.sync_api.Page, solara_server, solara_app, extra_include_path):
    page_session.context.clear_cookies()
    with extra_include_path(HERE), solara_app("server_test:StaticPage"):
        page_session.set_content(
            f"""
            <html>
            <body>
                <iframe name="main" src="{solara_server.base_url}"></iframe>
            </body>
            </html>
        """
        )

        iframe = page_session.frame("main")
        el = iframe.locator(".jupyter-widgets")
        assert el.text_content() == "Hello world"
