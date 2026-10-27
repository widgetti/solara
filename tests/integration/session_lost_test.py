import logging
import uuid
from pathlib import Path
from typing import List

import playwright.sync_api
import pytest

import solara
import solara.server.kernel_context
import solara.server.server
import solara.server.settings

HERE = Path(__file__).parent
MISMATCH_MESSAGE = "Session id mismatch when reusing kernel"
SESSION_COOKIE = solara.server.server.COOKIE_KEY_SESSION_ID

# the refresh dialog only exists for vuetify 2, vue 3 shows an alert
skip_vue3 = pytest.mark.skipif(solara.server.server.vue3, reason="the refresh dialog is vuetify 2 only")


@solara.component
def Page():
    value, set_value = solara.use_state(0)
    context = solara.server.kernel_context.get_current_context()
    assert context is not None
    solara.Text(f"Value {value}")

    def disconnect():
        assert len(context.kernel.session.websockets) == 1
        list(context.kernel.session.websockets)[0].close()

    solara.Button("Disconnect", on_click=disconnect)
    solara.Button("Increment", on_click=lambda: set_value(value + 1))


@pytest.fixture
def production(monkeypatch):
    # production mode turns off the dev-mode auto reload of the refresh dialog
    monkeypatch.setattr(solara.server.settings.main, "mode", "production")


@pytest.fixture
def force_refresh(monkeypatch):
    monkeypatch.setattr(solara.server.settings.theme, "force_refresh", True)


def _mismatch_records(caplog) -> List[logging.LogRecord]:
    return [r for r in caplog.records if r.levelno == logging.CRITICAL and MISMATCH_MESSAGE in r.getMessage()]


def _count_navigations(page: playwright.sync_api.Page) -> List[str]:
    navigations: List[str] = []

    def on_navigated(frame: playwright.sync_api.Frame):
        if frame == page.main_frame:
            navigations.append(frame.url)

    page.on("framenavigated", on_navigated)
    return navigations


def _session_cookie(page: playwright.sync_api.Page):
    values = [c["value"] for c in page.context.cookies() if c["name"] == SESSION_COOKIE]
    return values[0] if values else None


def _load(page: playwright.sync_api.Page, url: str) -> "solara.server.kernel_context.VirtualKernelContext":
    page.goto(url)
    page.locator("text=Value 0").wait_for()
    page.locator("text=Increment").click()
    page.locator("text=Value 1").wait_for()
    assert len(solara.server.kernel_context.contexts) == 1
    return list(solara.server.kernel_context.contexts.values())[0]


def _lose_session_and_reconnect(page: playwright.sync_api.Page, caplog):
    page.context.clear_cookies()
    assert _session_cookie(page) is None
    # the server closes the websocket, and the client reconnects without the session cookie
    page.locator("text=Disconnect").click()
    for _ in range(100):
        if _mismatch_records(caplog):
            break
        page.wait_for_timeout(100)
    assert len(_mismatch_records(caplog)) == 1


@skip_vue3
def test_session_lost_shows_refresh_dialog(page_session: playwright.sync_api.Page, solara_server, solara_app, extra_include_path, production, caplog):
    with extra_include_path(HERE), solara_app("session_lost_test:Page"):
        caplog.set_level(logging.INFO)
        _load(page_session, solara_server.base_url)
        navigations = _count_navigations(page_session)
        _lose_session_and_reconnect(page_session, caplog)
        page_session.locator("text=Refresh now").wait_for(timeout=10_000)
        # the client stops reconnecting: a reconnect would log a new mismatch every 0.5 seconds
        page_session.wait_for_timeout(2000)
        assert len(_mismatch_records(caplog)) == 1
        assert navigations == []
        # the session lost overlay is hidden behind the dialog
        assert not page_session.locator("text=Server disconnected").is_visible()

        page_session.locator("text=Refresh now").click()
        page_session.locator("text=Value 0").wait_for()
        assert len(navigations) == 1
        assert _session_cookie(page_session) is not None
        page_session.locator("text=Increment").click()
        page_session.locator("text=Value 1").wait_for()
        assert len(_mismatch_records(caplog)) == 1
        page_session.goto("about:blank")


def test_session_lost_force_refresh_reloads_once(
    page_session: playwright.sync_api.Page, solara_server, solara_app, extra_include_path, production, force_refresh, caplog
):
    with extra_include_path(HERE), solara_app("session_lost_test:Page"):
        caplog.set_level(logging.INFO)
        context = _load(page_session, solara_server.base_url)
        old_session_id = context.session_id
        assert _session_cookie(page_session) == old_session_id
        navigations = _count_navigations(page_session)
        _lose_session_and_reconnect(page_session, caplog)
        page_session.locator("text=Value 0").wait_for(timeout=10_000)
        # give a reload loop the time to show itself
        page_session.wait_for_timeout(2000)
        assert len(navigations) == 1
        new_session_id = _session_cookie(page_session)
        assert new_session_id is not None
        assert new_session_id != old_session_id
        new_contexts = [c for c in solara.server.kernel_context.contexts.values() if c is not context and not c.closed_event.is_set()]
        assert len(new_contexts) == 1
        assert new_contexts[0].id != context.id
        assert new_contexts[0].session_id == new_session_id
        page_session.locator("text=Increment").click()
        page_session.locator("text=Value 1").wait_for()
        assert len(_mismatch_records(caplog)) == 1
        page_session.goto("about:blank")


def test_reconnect_with_session_cookie_has_no_dialog(page_session: playwright.sync_api.Page, solara_server, solara_app, extra_include_path, production, caplog):
    with extra_include_path(HERE), solara_app("session_lost_test:Page"):
        caplog.set_level(logging.INFO)
        context = _load(page_session, solara_server.base_url)
        navigations = _count_navigations(page_session)
        ws = list(context.kernel.session.websockets)[0]
        page_session.locator("text=Disconnect").click()
        for _ in range(50):
            if ws not in context.kernel.session.websockets and len(context.kernel.session.websockets) == 1:
                break
            page_session.wait_for_timeout(100)
        else:
            raise RuntimeError("Timeout waiting for reconnected websocket")
        page_session.locator("text=Increment").click()
        page_session.locator("text=Value 2").wait_for()
        assert not page_session.locator("text=Refresh now").is_visible()
        assert _mismatch_records(caplog) == []
        assert navigations == []
        assert len(solara.server.kernel_context.contexts) == 1
        page_session.goto("about:blank")
        assert context.closed_event.wait(10)


@skip_vue3
def test_session_lost_with_pinned_kernel_id_shows_dialog(
    page_session: playwright.sync_api.Page, solara_server, solara_app, extra_include_path, production, force_refresh, caplog
):
    # a reload keeps ?kernelid=, so it would hit the same kernel with the new session again:
    # even with force_refresh on, show the dialog
    with extra_include_path(HERE), solara_app("session_lost_test:Page"):
        caplog.set_level(logging.INFO)
        kernel_id = str(uuid.uuid4())
        context = _load(page_session, solara_server.base_url + f"?kernelid={kernel_id}")
        assert context.id == kernel_id
        navigations = _count_navigations(page_session)
        _lose_session_and_reconnect(page_session, caplog)
        page_session.locator("text=Refresh now").wait_for(timeout=10_000)
        page_session.wait_for_timeout(2000)
        assert navigations == []
        assert len(_mismatch_records(caplog)) == 1
        page_session.goto("about:blank")
