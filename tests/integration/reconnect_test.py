from pathlib import Path
from typing import Optional

import playwright.sync_api

import solara
import solara.server.kernel_context

HERE = Path(__file__).parent


set_value = None
context: Optional["solara.server.kernel_context.VirtualKernelContext"] = None


@solara.component
def Page():
    global set_value, app_context
    value, set_value = solara.use_state(0)
    assert set_value is not None
    context = solara.server.kernel_context.get_current_context()
    assert context is not None
    solara.Text(f"Value {value}")

    def disconnect():
        assert len(context.kernel.session.websockets) == 1
        list(context.kernel.session.websockets)[0].close()

    solara.Button("Disconnect", on_click=disconnect)
    solara.Button("Increment", on_click=lambda: set_value(value + 1))

    def disconnect_and_change():
        assert len(context.kernel.session.websockets) == 1
        list(context.kernel.session.websockets)[0].close()
        set_value(100)

    solara.Button("Disconnect and change", on_click=disconnect_and_change)


def test_reconnect_simple(browser: playwright.sync_api.Browser, page_session: playwright.sync_api.Page, solara_server, solara_app, extra_include_path):
    with extra_include_path(HERE), solara_app("reconnect_test:Page"):
        page_session.goto(solara_server.base_url)
        page_session.locator("text=Value 0").wait_for()
        page_session.locator("text=Increment").click()
        page_session.locator("text=Value 1").wait_for()
        assert len(solara.server.kernel_context.contexts) == 1
        context = list(solara.server.kernel_context.contexts.values())[0]
        assert len(context.kernel.session.websockets) == 1
        ws = list(context.kernel.session.websockets)[0]
        page_session.locator("text=Disconnect").nth(0).click()
        n = 0
        # we wait till the current websocket is not connected anymore, and a different one is connected
        while not (ws not in context.kernel.session.websockets and len(context.kernel.session.websockets) == 1):
            page_session.wait_for_timeout(100)
            n += 1
            if n > 50:
                raise RuntimeError("Timeout waiting for reconnected websocket")
        page_session.locator("text=Value 1").wait_for()
        page_session.locator("text=Increment").click()
        page_session.locator("text=Value 2").wait_for()
        # we should not have created a new context
        assert len(solara.server.kernel_context.contexts) == 1
        page_session.goto("about:blank")
        assert context.closed_event.wait(10)


def test_reconnect_fail(browser: playwright.sync_api.Browser, page_session: playwright.sync_api.Page, solara_server, solara_app, extra_include_path):
    with extra_include_path(HERE), solara_app("reconnect_test:Page"):
        # import reconnect_test as module

        page_session.goto(solara_server.base_url)
        page_session.locator("text=Value 0").wait_for()
        page_session.locator("text=Increment").click()
        page_session.locator("text=Value 1").wait_for()
        cull_timeout_previous = solara.server.settings.kernel.cull_timeout
        context = None
        try:
            solara.server.settings.kernel.cull_timeout = "0s"
            assert len(solara.server.kernel_context.contexts) == 1
            context = list(solara.server.kernel_context.contexts.values())[0]
            assert len(context.kernel.session.websockets) == 1
            page_session.locator("text=Disconnect").nth(0).click()
            page_session.locator("text=Could not restore session").wait_for()
            n = 0
            # we wait till the all contexts are closed
            while len(solara.server.kernel_context.contexts):
                page_session.wait_for_timeout(100)
                n += 1
                if n > 50:
                    raise RuntimeError("Timeout waiting for kernel shutdown")

        finally:
            page_session.goto("about:blank")
            if context is not None:
                assert context.closed_event.wait(10)
            solara.server.settings.kernel.cull_timeout = cull_timeout_previous


def test_reconnect_and_update(browser: playwright.sync_api.Browser, page_session: playwright.sync_api.Page, solara_server, solara_app, extra_include_path):
    with extra_include_path(HERE), solara_app("reconnect_test:Page"):
        page_session.goto(solara_server.base_url)
        page_session.locator("text=Value 0").wait_for()
        page_session.locator("text=Increment").click()
        page_session.locator("text=Value 1").wait_for()

        assert len(solara.server.kernel_context.contexts) == 1
        context = list(solara.server.kernel_context.contexts.values())[0]

        # this will mutate when disconnected, testing the update functionality on reconnect
        page_session.locator("text=Disconnect and change").click()
        page_session.locator("text=Value 100").wait_for()
        page_session.goto("about:blank")
        assert context.closed_event.wait(10)
