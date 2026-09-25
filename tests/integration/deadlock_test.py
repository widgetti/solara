import time
from pathlib import Path

import playwright.sync_api
import pytest
import requests

import solara
import solara.server.kernel_context
import solara.server.settings
from solara.server import kernel_context, server
from solara.server.starlette import ServerStarlette

HERE = Path(__file__).parent

progress = solara.reactive(0)


@solara.component
def BusyApp():
    """Button whose handler stays busy for ~10s while pushing widget updates."""

    def start():
        for i in range(40):
            progress.value = i
            time.sleep(0.25)

    solara.Button(label="start", on_click=start)
    solara.Text(f"progress {progress.value}")


@pytest.fixture
def eviction_enabled(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(solara.server.settings.state, "test_eviction", True)
    if solara.server.settings.main.mode == "production":
        monkeypatch.setattr(solara.server.settings.main, "mode", "development")
    yield


def test_evict_while_handler_busy_does_not_deadlock(
    browser: playwright.sync_api.Browser,
    page_session: playwright.sync_api.Page,
    solara_server,
    solara_app,
    extra_include_path,
    eviction_enabled,
):
    """Regression test: closing a kernel must never happen on the event loop thread.

    A busy event handler holds ``context.lock`` and pushes widget updates through
    ``portal.call``, which needs the event loop. If the evict route calls
    ``context.close()`` inline, the loop blocks on the lock while the handler blocks on
    the loop, and the whole server stops answering (even ``/readyz``).
    """
    if not isinstance(solara_server, ServerStarlette):
        pytest.skip("the eviction route and the off-loop close are starlette-only")

    with extra_include_path(HERE), solara_app("deadlock_test:BusyApp"):
        kernel_context.contexts.clear()
        page_session.goto(solara_server.base_url)
        page_session.locator("text=progress 0").wait_for()
        page_session.locator("button:has-text('start')").click()
        # the handler is now running and sending widget updates
        page_session.locator("text=progress 2").wait_for()

        kernel_ids = [id for id in kernel_context.contexts if id != "dummy"]
        assert len(kernel_ids) == 1, f"expected 1 kernel, got {kernel_ids}"
        kernel_id = kernel_ids[0]
        context = kernel_context.contexts[kernel_id]

        cookies = page_session.context.cookies()
        session_ids = [c["value"] for c in cookies if c["name"] == server.COOKIE_KEY_SESSION_ID]
        assert session_ids, f"no {server.COOKIE_KEY_SESSION_ID} cookie: {cookies}"

        url = f"{solara_server.base_url}/_solara/api/evict/{kernel_id}"
        response = requests.post(url, cookies={server.COOKIE_KEY_SESSION_ID: session_ids[0]}, timeout=15)
        assert response.status_code == 200, response.text

        # the server must still serve other requests (it would not if the loop deadlocked)
        assert requests.get(f"{solara_server.base_url}/readyz", timeout=5).status_code == 200

        assert context.closed_event.wait(30)
