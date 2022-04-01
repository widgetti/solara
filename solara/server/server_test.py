import contextlib
import logging
import sys
import threading
import time

import playwright
import playwright.sync_api
import pytest
import react_ipywidgets as react
import react_ipywidgets.ipywidgets as w
import requests

import solara
from solara.kitchensink import v

from . import app
from .fastapi import app as app_starlette

logger = logging.getLogger("solara.server.test")

TEST_PORT = 18765


# see https://github.com/microsoft/playwright-pytest/issues/23
@pytest.fixture
def context(context):
    context.set_default_timeout(3000)
    yield context


class Server(threading.Thread):
    def __init__(self, port, host="localhost", **kwargs):
        self.port = port
        self.host = host
        self.base_url = f"http://{self.host}:{self.port}"

        self.kwargs = kwargs
        self.started = threading.Event()
        self.stopped = threading.Event()
        super().__init__(name="fastapi-thread")
        self.setDaemon(True)

    def run(self):
        self.mainloop()

    def serve_threaded(self):
        logger.debug("start thread")
        self.start()
        logger.debug("wait for thread to run")
        self.started.wait()
        logger.debug("make tornado io loop the main thread's current")

    def wait_until_serving(self):
        for n in range(10):
            url = f"http://{self.host}:{self.port}/"
            try:
                response = requests.get(url)
            except requests.exceptions.ConnectionError:
                pass
            else:
                if response.status_code == 200:
                    return
            time.sleep(0.05)
        else:
            raise RuntimeError(f"Server at {url} does not seem to be running")

    def mainloop(self):
        logger.info("serving at http://%s:%d" % (self.host, self.port))

        from uvicorn.config import Config
        from uvicorn.server import Server

        if sys.version_info[:2] < (3, 7):
            # make python 3.6 work
            import asyncio

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # uvloop will trigger a: RuntimeError: There is no current event loop in thread 'fastapi-thread'
        config = Config(app_starlette, host=self.host, port=self.port, **self.kwargs, loop="asyncio")
        self.server = Server(config=config)
        self.started.set()
        try:
            self.server.run()
        except:  # noqa: E722
            logger.exception("Oops, server stopped unexpectedly")
        finally:
            self.stopped.set()

    def stop_serving(self):
        logger.debug("stopping server")
        print("STOP IT!")
        self.server.should_exit = True
        self.server.lifespan.should_exit = True
        if self.stopped.wait(1) is not None:
            logger.error("stopping server failed")
        logger.debug("stopped server")


@pytest.fixture()  # scope="module")
def solara_server():
    webserver = Server(TEST_PORT)
    webserver.serve_threaded()
    webserver.wait_until_serving()
    try:
        yield webserver
    finally:
        webserver.stop_serving()


@contextlib.contextmanager
def screenshot_on_error(page, path):
    try:
        yield
    except:  # noqa: E722
        page.screenshot(path=path)
        print(f"Saved screenshot to {path}", file=sys.stderr)
        raise


def test_docs_basics(page: playwright.sync_api.Page, solara_server):
    page.goto(solara_server.base_url)
    # with screenshot_on_error(page, 'tmp/test_docs_basics.png'):
    if 1:
        assert page.title() == "Hello from Solara ☀️"
        page.locator("text=Demo").click()

        page.locator("text=Calculator").click()
        page.locator("text=+/-").wait_for()
        page.screenshot(path="tmp/screenshot_calculator.png")

        page.locator("text=Bqplot").click()
        page.locator("text=Line color").wait_for()
        page.screenshot(path="tmp/screenshot_bqplot.png")

        page.locator("text=Plotly").click()
        page.locator("text=plotly express").wait_for()
        page.screenshot(path="tmp/screenshot_plotly.png")

        page.locator("text=Altair").click()
        page.locator("text=Altair is supported").wait_for()
        page.screenshot(path="tmp/screenshot_altair.png")

        page.locator("text=Docs").click()
        page.screenshot(path="tmp/screenshot_debug.png")
        page.locator('div[role="tab"]:has-text("use_state")').wait_for()
        page.screenshot(path="tmp/screenshot_docs.png")

        page.locator('div[role="tab"]:has-text("use_state")').click()
        page.locator("text=use_state can be used").wait_for()
        page.screenshot(path="tmp/screenshot_use_state.png")

        page.locator('div[role="tab"]:has-text("use_effect")').click()
        page.locator("text=use_side_effect can be used").wait_for()
        page.screenshot(path="tmp/screenshot_use_effect.png")


@react.component
def ClickButton():
    count, set_count = react.use_state(0)
    if not isinstance(count, int):
        print("oops, state issue?")
        count = 0
    # return w.Button()  # description=, on_click=set_count(count + 1))
    btn = v.Btn(children=[f"Clicked: {count}"])
    v.use_event(btn, "click", lambda *ignore: set_count(count + 1))
    return btn


click_button = ClickButton()


def test_multi_user(page: playwright.sync_api.Page, solara_server):
    solara.server.server.solara_app = app.AppScript("solara.server.server_test:click_button")
    page.goto(solara_server.base_url)
    with screenshot_on_error(page, "tmp/test_docs_basics.png"):
        assert page.title() == "Hello from Solara ☀️"
        page.screenshot(path="tmp/screenshot_test_click.png")

        # page.locator("text=Clicked: 0").click()


@react.component
def ThreadTest():
    label, set_label = react.use_state("initial")
    use_thread, set_use_thread = react.use_state(False)

    def from_thread():
        set_label("from thread")

    def start_thread():
        if use_thread:
            thread = threading.Thread(target=from_thread)
            thread.start()
            return thread.join

    react.use_side_effect(start_thread, [use_thread])
    # we need to trigger creating a new widget, to make sure we
    # invoke a solara.server.app.get_current_context
    if label == "initial":
        return w.Button(description=label, on_click=lambda: set_use_thread(True))
    else:
        return w.Label(value=label)


thread_test = ThreadTest()
# click_button = ThreadTest()


def test_from_thread(page: playwright.sync_api.Page, solara_server):
    solara.server.server.solara_app = app.AppScript("solara.server.server_test:thread_test")
    page.goto(solara_server.base_url)

    assert page.title() == "Hello from Solara ☀️"
    el = page.locator(".jupyter-widgets")
    assert el.text_content() == "initial"
    page.wait_for_timeout(500)
    el.click()
    page.locator("text=from thread").wait_for()


def test_state(page: playwright.sync_api.Page, solara_server):
    solara.server.server.solara_app = app.AppScript("solara.server.server_test:click_button")
    page.goto(solara_server.base_url)
    # with screenshot_on_error(page, "tmp/test_state.png"):
    assert page.title() == "Hello from Solara ☀️"
    page.locator("text=Clicked: 0").click()
    page.locator("text=Clicked: 1").click()
    # refresh...
    page.goto(solara_server.base_url)
    # and state should be restored
    page.locator("text=Clicked: 2").wait_for()
    # account button
    page.locator("button >> nth=1").click()
    # reset state button
    page.locator('[role="menuitem"]').click()
    # refresh manually
    page.goto(solara_server.base_url)
    # and state should be restored
    page.locator("text=Clicked: 0").wait_for()


def test_from_thread_two_users(browser: playwright.sync_api.Browser, solara_server):
    solara.server.server.solara_app = app.AppScript("solara.server.server_test:thread_test")

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
