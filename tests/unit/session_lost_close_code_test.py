import time

import pytest
from starlette.applications import Starlette
from starlette.routing import WebSocketRoute
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

import solara.server.settings
from solara.server import kernel_context
from solara.server.starlette import kernel_connection

KERNEL_ID = "kernel-session-lost"


@pytest.fixture
def client():
    app = Starlette(routes=[WebSocketRoute("/jupyter/api/kernels/{kernel_id}/{name}", endpoint=kernel_connection)])
    try:
        with TestClient(app) as client:
            yield client
    finally:
        for context in list(kernel_context.contexts.values()):
            context.close()


def _connect(client: TestClient, session_id: str, page_id: str):
    return client.websocket_connect(
        f"/jupyter/api/kernels/{KERNEL_ID}/channels?session_id={page_id}",
        headers={"cookie": f"solara-session-id={session_id}"},
    )


@pytest.mark.parametrize("threaded", [True, False])
def test_reconnect_with_other_session_cookie_closes_with_session_lost_code(client, no_kernel_context, monkeypatch, threaded):
    monkeypatch.setattr(solara.server.settings.kernel, "threaded", threaded)
    with _connect(client, "session-a", "page-1"):
        # the kernel is created after the websocket is accepted
        deadline = time.monotonic() + 5
        while KERNEL_ID not in kernel_context.contexts and time.monotonic() < deadline:
            time.sleep(0.01)
        assert kernel_context.contexts[KERNEL_ID].session_id == "session-a"
        # a reconnect to the same kernel, but the session cookie got lost or changed
        with _connect(client, "session-b", "page-1") as ws:
            if threaded:
                # without kernel threads the text goes out in a task that the close beats
                assert "please reload the page" in ws.receive_text()
            with pytest.raises(WebSocketDisconnect) as exc_info:
                ws.receive_text()
            # the literal, not SESSION_LOST_CLOSE_CODE: main-vuetify.js has its own copy of the value
            assert exc_info.value.code == 4001
            assert exc_info.value.reason == "session id mismatch"
        # the kernel still belongs to the first session
        assert kernel_context.contexts[KERNEL_ID].session_id == "session-a"
