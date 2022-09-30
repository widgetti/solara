import contextlib
import logging
import sys
import threading
from pathlib import Path

import playwright
import playwright.sync_api
import reacton.ipywidgets as w
import solara
from solara.kitchensink import v

logger = logging.getLogger("solara.server.test")
HERE = Path(__file__).parent


@contextlib.contextmanager
def screenshot_on_error(page, path):
    try:
        yield
    except:  # noqa: E722
        page.screenshot(path=path)
        print(f"Saved screenshot to {path}", file=sys.stderr)  # noqa
        raise


def test_docs_basics(page: playwright.sync_api.Page, solara_server, solara_app):
    # with screenshot_on_error(page, 'tmp/test_docs_basics.png'):
    with solara_app("solara.website.pages"):
        page.goto(solara_server.base_url)
        assert page.title() == "Hello from Solara ☀️"
        page.locator('div[role="tab"]:has-text("Examples")').click()

        page.locator("text=Calculator").click()
        page.locator("text=+/-").wait_for()
        page.screenshot(path="tmp/screenshot_calculator.png")

        page.locator("text=Bqplot").click()
        page.locator("text=Line color").wait_for()
        page.screenshot(path="tmp/screenshot_bqplot.png")

        page.locator("text=Plotly").first.click()
        page.locator("text=plotly express").wait_for()
        page.screenshot(path="tmp/screenshot_plotly.png")

        page.locator("text=Altair").click()
        page.locator("text=Altair is supported").wait_for()
        page.screenshot(path="tmp/screenshot_altair.png")

        # page.locator("text=Docs").click()
        # page.screenshot(path="tmp/screenshot_debug.png")
        # page.locator('div[role="tab"]:has-text("use_state")').wait_for()
        # page.screenshot(path="tmp/screenshot_docs.png")

        # page.locator('div[role="tab"]:has-text("use_state")').click()
        # page.locator("text=use_state can be used").wait_for()
        # page.screenshot(path="tmp/screenshot_use_state.png")

        # page.locator('div[role="tab"]:has-text("use_effect")').click()
        # page.locator("text=use_side_effect can be used").wait_for()
        # page.screenshot(path="tmp/screenshot_use_effect.png")


@solara.component
def ClickButton():
    count, set_count = solara.use_state(0)
    if not isinstance(count, int):
        print("oops, state issue?")  # noqa
        count = 0
    btn = v.Btn(children=[f"Clicked: {count}"])

    def on_click(*ignore):
        set_count(count + 1)

    v.use_event(btn, "click", on_click)
    return btn


click_button = ClickButton()


def test_multi_user(page: playwright.sync_api.Page, solara_server, solara_app, extra_include_path):
    with extra_include_path(HERE), solara_app("server_test:click_button"):
        page.goto(solara_server.base_url)
        assert page.title() == "Hello from Solara ☀️"
        page.screenshot(path="tmp/screenshot_test_click.png")

        # page.locator("text=Clicked: 0").click()


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


thread_test = ThreadTest()
# click_button = ThreadTest()


def test_from_thread(page: playwright.sync_api.Page, solara_server, solara_app, extra_include_path):
    with extra_include_path(HERE), solara_app("server_test:thread_test"):
        page.goto(solara_server.base_url)

        assert page.title() == "Hello from Solara ☀️"
        el = page.locator(".jupyter-widgets")
        assert el.text_content() == "initial"
        page.wait_for_timeout(500)
        el.click()
        page.locator("text=from thread").wait_for()


def test_state(page: playwright.sync_api.Page, solara_server, solara_app, extra_include_path):
    with extra_include_path(HERE), solara_app("server_test:click_button"):
        page.goto(solara_server.base_url)
        # with screenshot_on_error(page, "tmp/test_state.png"):
        assert page.title() == "Hello from Solara ☀️"
        page.locator("text=Clicked: 0").click()
        page.locator("text=Clicked: 1").click()
        # refresh...
        page.goto(solara_server.base_url)
        # and state should NOT be restored
        page.locator("text=Clicked: 0").wait_for()


def test_from_thread_two_users(browser: playwright.sync_api.Browser, solara_server, solara_app, extra_include_path):
    with extra_include_path(HERE), solara_app("server_test:thread_test"):
        context1 = browser.new_context()
        page1 = context1.new_page()
        context2 = browser.new_context()
        page2 = context2.new_page()

        page1.goto(solara_server.base_url)

        assert page1.title() == "Hello from Solara ☀️"
        el1 = page1.locator(".jupyter-widgets")
        assert el1.text_content() == "initial"

        page2.goto(solara_server.base_url)
        assert page2.title() == "Hello from Solara ☀️"
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


# def test_two_clients(browser: playwright.sync_api.Browser):
#     context1 = browser.new_context()
#     page1 = context1.new_page()
#     context2 = browser.new_context()
#     page2 = context1.new_page()
