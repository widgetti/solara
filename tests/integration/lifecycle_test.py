import threading
from pathlib import Path
from typing import cast

import playwright.sync_api
import pytest
from reacton.core import _RenderContext

import solara.server.kernel_context
import solara.server.server
import solara.server.settings
from solara.server import kernel_context

HERE = Path(__file__).parent


@solara.component
def ClickButton(label="Clicks"):
    clicks = solara.use_reactive(0)
    solara.Button(label=f"{label}-{clicks.value}", on_click=lambda: clicks.set(clicks.value + 1))


@pytest.fixture
def short_cull_timeout():
    cull_timeout_previous = solara.server.settings.kernel.cull_timeout
    solara.server.settings.kernel.cull_timeout = "4.0s"
    try:
        yield
    finally:
        solara.server.settings.kernel.cull_timeout = cull_timeout_previous


def test_kernel_lifecycle_close_single(
    short_cull_timeout,
    browser: playwright.sync_api.Browser,
    page_session: playwright.sync_api.Page,
    solara_server,
    solara_app,
    extra_include_path,
):
    with extra_include_path(HERE), solara_app("lifecycle_test:ClickButton"):
        kernel_context.contexts.clear()
        page_session.goto(solara_server.base_url)
        page_session.locator("text=Clicks-0").click()
        contexts = list(kernel_context.contexts.values())
        assert len(contexts) == 1
        context = contexts[0]
        assert not context.closed_event.is_set()
        page_session.goto("about:blank")
        page_session.wait_for_timeout(100)
        assert context.closed_event.is_set()


def test_kernel_lifecycle_close_while_disconnected(
    short_cull_timeout,
    browser: playwright.sync_api.Browser,
    page_session: playwright.sync_api.Page,
    solara_server,
    solara_app,
    extra_include_path,
):
    with extra_include_path(HERE), solara_app("lifecycle_test:ClickButton"):
        kernel_context.contexts.clear()
        page_session.goto(solara_server.base_url + "?solara-no-close-beacon")
        page_session.locator("text=Clicks-0").click()
        contexts = list(kernel_context.contexts.values())
        assert len(contexts) == 1
        context = contexts[0]
        assert not context.closed_event.is_set()
        page_session.wait_for_timeout(100)
        page_session.goto("about:blank")

        kernel_id = context.id
        rc = cast(_RenderContext, context.app_object)
        widget = rc.container
        assert widget is not None
        model_id = widget._model_id

        page_session.goto(solara_server.base_url + f"?kernelid={kernel_id}&modelid={model_id}")
        # make sure the page is functional
        page_session.locator("text=Clicks-1").click()
        page_session.locator("text=Clicks-2").wait_for()
        page_session.goto("about:blank")
        # give a bit of time to make sure the cull task is started
        page_session.wait_for_timeout(100)
        cull_task_2 = context._last_kernel_cull_task
        assert cull_task_2 is not None
        # we can't mix do async, so we hook up an event to the Future
        event = threading.Event()
        cull_task_2.add_done_callback(lambda x: event.set())
        event.wait()
        assert context.closed_event.is_set()
