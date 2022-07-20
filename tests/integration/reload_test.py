import contextlib
import logging
from pathlib import Path

import playwright.sync_api

from solara.server import reload

app_path = Path(__file__).parent / "testapp.py"

logger = logging.getLogger("solara-test.integration.reload_test")


@contextlib.contextmanager
def append(text):
    with app_path.open() as f:
        content = f.read()
    try:
        with app_path.open("w") as f:
            f.write(content)
            f.write(text)
        yield
    finally:
        with app_path.open("w") as f:
            f.write(content)


@contextlib.contextmanager
def replace(path, text):
    with path.open() as f:
        content = f.read()
    try:
        with path.open("w") as f:
            f.write(text)
        yield
    finally:
        with path.open("w") as f:
            f.write(content)


def test_reload_syntax_error(page: playwright.sync_api.Page, solara_server, solara_app, extra_include_path):
    with extra_include_path(app_path.parent), solara_app("testapp:app"):
        # use as module, otherwise pickle wil not work
        page.goto(solara_server.base_url)
        assert page.title() == "Hello from Solara ☀️"
        page.locator("text=Clicked 0 times").click()
        page.locator("text=Clicked 1 times").click()

        with append("\n$%#$%"):
            reload.reloader.reload_event_next.wait()
            # page.locator("text=Clicked 2 times").click()
            page.locator("text=SyntaxError").wait_for()
        reload.reloader.reload_event_next.wait()
        page.locator("text=Clicked 2 times").click()
        page.locator("text=Clicked 3 times").wait_for()


def test_reload_many(page: playwright.sync_api.Page, solara_server, solara_app, extra_include_path):
    with extra_include_path(app_path.parent), solara_app("testapp:app"):
        logger.info("test_reload_many:run app")
        # use as module, otherwise pickle wil not work
        page.goto(solara_server.base_url)
        assert page.title() == "Hello from Solara ☀️"
        page.locator("text=Clicked 0 times").click()
        page.locator("text=Clicked 1 times").click()

        logger.info("test_reload_many:Touch app 1st time")
        app_path.touch()
        reload.reloader.reload_event_next.wait()
        page.locator("text=Clicked 2 times").click()
        page.locator("text=Clicked 3 times").wait_for(state="visible")

        logger.info("test_reload_many:Touch app 2st time")
        app_path.touch()
        reload.reloader.reload_event_next.wait()
        page.locator("text=Clicked 3 times").click()
        page.locator("text=Clicked 4 times").wait_for(state="visible")


def test_reload_vue(page: playwright.sync_api.Page, solara_server, solara_app, extra_include_path):
    with extra_include_path(app_path.parent), solara_app("testapp:VueTestApp"):
        page.goto(solara_server.base_url)
        assert page.title() == "Hello from Solara ☀️"
        page.locator("text=foobar").wait_for()

        vuecode = """
<template>
  <div>RELOADED</div>
</template>
        """
        vuepath = Path(__file__).parent / "test.vue"
        with replace(vuepath, vuecode):
            page.locator("text=RELOADED").wait_for()
        page.locator("text=foobar").wait_for()
