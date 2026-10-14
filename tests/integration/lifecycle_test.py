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
        page_session.wait_for_timeout(500)
        page_session.goto("about:blank")
        assert context.closed_event.wait(timeout=20)


@pytest.mark.skip(reason="This test is flaky, re-enable when we have a more stable solution")
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
        assert context.closed_event.wait(timeout=20)


@solara.component
def ClickButtonAndDownloadLink():
    ClickButton()
    # a plain link to a file the server sends as an attachment, the browser saves it and stays
    solara.v.Html(tag="a", attributes={"href": "report.csv", "id": "download"}, children=["Download"])


def test_kernel_survives_a_download_link(
    browser: playwright.sync_api.Browser,
    context_session: playwright.sync_api.BrowserContext,
    solara_server,
    solara_app,
    extra_include_path,
):
    # Our own page: the route below intercepts requests of the page it is on, and on the shared
    # page_session it would also catch the close beacons that later tests send from pagehide.
    page = context_session.new_page()
    try:
        with extra_include_path(HERE), solara_app("lifecycle_test:ClickButtonAndDownloadLink"):
            kernel_context.contexts.clear()
            page.route(
                "**/report.csv",
                lambda route: route.fulfill(
                    body="a,b\n1,2\n", headers={"Content-Type": "text/csv", "Content-Disposition": 'attachment; filename="report.csv"'}
                ),
            )
            page.goto(solara_server.base_url)
            page.locator("text=Clicks-0").click()
            page.locator("text=Clicks-1").wait_for()
            context = list(kernel_context.contexts.values())[0]
            # the link starts a navigation (beforeunload fires), but the response is a download
            with page.expect_download():
                page.locator("#download").click()
            page.wait_for_timeout(500)
            assert page.url == solara_server.base_url + "/"
            # the page stays, so it must keep working
            page.locator("text=Clicks-1").click()
            page.locator("text=Clicks-2").wait_for()
            assert not context.closed_event.is_set()
    finally:
        page.close()


def test_page_restored_by_back_button_reloads(
    browser_type: playwright.sync_api.BrowserType,
    browser_name: str,
    solara_server,
    solara_app,
    extra_include_path,
):
    if browser_name != "chromium":
        pytest.skip("only chromium")
    # Playwright turns the back/forward cache off; the full chromium build (not the headless shell) has it
    browser = browser_type.launch(channel="chromium", ignore_default_args=["--disable-back-forward-cache"])
    try:
        page = browser.new_page()
        page.add_init_script("window.addEventListener('pageshow', (e) => { if (e.persisted) sessionStorage.setItem('restored', '1'); })")
        with extra_include_path(HERE), solara_app("lifecycle_test:ClickButton"):
            page.goto(solara_server.base_url)
            page.locator("text=Clicks-0").click()
            page.locator("text=Clicks-1").wait_for()
            page.goto(solara_server.base_url + "/static/assets/theme-light.css")
            page.wait_for_timeout(500)
            # not page.go_back(): it waits for a load event, which a page restored from memory does not fire
            page.evaluate("history.back()")
            # the page came back from memory with a closed kernel, so it must load again
            page.locator("text=Clicks-0").wait_for()
            assert page.evaluate("sessionStorage.getItem('restored')") == "1"
            page.locator("text=Clicks-0").click()
            page.locator("text=Clicks-1").wait_for()
    finally:
        browser.close()
