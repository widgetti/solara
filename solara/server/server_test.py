import contextlib
import logging
import sys
import threading
import time

import playwright
import playwright.sync_api
import pytest
import requests
from playwright.sync_api import sync_playwright

from .fastapi import app

logger = logging.getLogger('solara.server.test')

TEST_PORT = 18765


class Server(threading.Thread):
    def __init__(self, port, host='localhost', **kwargs):
        self.port = port
        self.host = host
        self.base_url = f'http://{self.host}:{self.port}'

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
            url = f'http://{self.host}:{self.port}/'
            try:
                response = requests.get(url)
            except requests.exceptions.ConnectionError:
                pass
            else:
                if response.status_code == 200:
                    return
            time.sleep(0.05)
        else:
            raise RuntimeError(f'Server at {url} does not seem to be running')

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
        config = Config(app, host=self.host, port=self.port, **self.kwargs, loop='asyncio')
        self.server = Server(config=config)
        self.started.set()
        try:
            self.server.run()
        except:
            logger.exception("Oops, server stopped unexpectedly")
        finally:
            self.stopped.set()

    def stop_serving(self):
        logger.debug("stopping server")
        self.server.should_exit = True
        if self.stopped.wait(1) is not None:
            logger.error('stopping server failed')
        logger.debug("stopped server")


@pytest.fixture(scope="session")
def server():
    webserver = Server(TEST_PORT)
    webserver.serve_threaded()
    webserver.wait_until_serving()
    yield webserver
    webserver.stop_serving()


@contextlib.contextmanager
def screenshot_on_error(page, path):
    try:
        yield
    except:
        page.screenshot(path=path)
        print(f'Saved screenshot to {path}', file=sys.stderr)
        raise


def test_docs_basics(page: playwright.sync_api.Page, server):
    page.goto(server.base_url)
    # with screenshot_on_error(page, 'tmp/test_docs_basics.png'):
    if 1:
        assert page.title() == 'Hello from Solara ☀️'
        page.locator("text=Demo: calculator").click()
        page.locator("text=+/-").wait_for()
        page.screenshot(path="tmp/screenshot_calculator.png")

        page.locator("text=Demo: bqplot").click()
        page.locator("text=Line color").wait_for()
        page.screenshot(path="tmp/screenshot_bqplot.png")

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


# def test_two_clients(browser: playwright.sync_api.Browser):
#     context1 = browser.new_context()
#     page1 = context1.new_page()
#     context2 = browser.new_context()
#     page2 = context1.new_page()
