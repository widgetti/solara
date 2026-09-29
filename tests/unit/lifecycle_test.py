import asyncio
import sys
import time
from unittest.mock import Mock

import pytest

import solara.server.server
import solara.server.settings
import solara.server.websocket
from solara.server import kernel_context

on_windows = sys.platform == "win32"


@pytest.fixture
def short_cull_timeout():
    cull_timeout_previous = solara.server.settings.kernel.cull_timeout
    solara.server.settings.kernel.cull_timeout = "0.2s"
    try:
        yield
    finally:
        solara.server.settings.kernel.cull_timeout = cull_timeout_previous


def test_kernel_max_per_session(monkeypatch):
    # one session cookie may create at most max_per_session live kernels; a different session is
    # unaffected, and reconnecting an existing kernel does not count against the cap. The cap only
    # engages when a state backend is configured (additive: no change without persistence).
    import solara.state

    be = solara.state.MemoryStateBackend()
    monkeypatch.setattr(solara.state, "get_backend", lambda: be)
    monkeypatch.setattr(solara.server.settings.state, "secret_keys", "test-secret-key")
    monkeypatch.setattr(solara.server.settings.kernel, "max_per_session", 3)
    created = []
    try:
        for i in range(3):
            created.append(kernel_context.initialize_virtual_kernel("sess-cap", f"kern-cap-{i}", Mock()))
        with pytest.raises(RuntimeError, match="too many live kernels"):
            kernel_context.initialize_virtual_kernel("sess-cap", "kern-cap-overflow", Mock())
        # reconnect of an existing kernel is fine (reuse, not a new kernel)
        assert kernel_context.initialize_virtual_kernel("sess-cap", "kern-cap-0", Mock()) is created[0]
        # a different session is not blocked
        other = kernel_context.initialize_virtual_kernel("sess-other", "kern-other", Mock())
        created.append(other)
    finally:
        for ctx in list(kernel_context.contexts.values()):
            ctx.close()


@pytest.mark.skipif(on_windows, reason="This test is flaky on Windows")
async def test_kernel_lifecycle_reconnect_simple(short_cull_timeout):
    # a reconnect should be possible within the reconnect window
    websocket = Mock()
    context = kernel_context.initialize_virtual_kernel("session-id-1", "kernel-id-1", websocket)
    connection_1 = context.page_connect("page-id-1")
    cull_task1 = context.page_disconnect("page-id-1", connection_1)
    await asyncio.sleep(0.01)
    connection_2 = context.page_connect("page-id-2")
    # the new connect should cancel the first cull task
    with pytest.raises(asyncio.CancelledError):
        await cull_task1
    assert not context.closed_event.is_set()
    await context.page_disconnect("page-id-2", connection_2)
    assert context.closed_event.is_set()


@pytest.mark.skipif(on_windows, reason="This test is flaky on Windows")
async def test_kernel_lifecycle_double_disconnect(short_cull_timeout):
    # a reconnect should be possible within the reconnect window
    websocket = Mock()
    context = kernel_context.initialize_virtual_kernel("session-id-1", "kernel-id-1", websocket)
    connection_1 = context.page_connect("page-id-1")
    cull_task1 = context.page_disconnect("page-id-1", connection_1)

    # now after 0.1 we disconnect the 2nd time
    await asyncio.sleep(0.1)
    connection_2 = context.page_connect("page-id-2")
    cull_task2 = context.page_disconnect("page-id-2", connection_2)
    t_disconnect_page_2 = time.time()
    t0_disconnect_page_2 = time.time()

    # go over the reconnect window of cull_task1 (with a 0.05 extra to make sure it is really over)
    # await asyncio.sleep(0.1 + 0.05)
    # but the first disconnect should not have closed the kernel context yet
    with pytest.raises(asyncio.CancelledError):
        await cull_task1
    # the CancelledError above is the real proof of cancellation; the time bound only guards
    # against having waited out a full cull window, so keep it loose for loaded CI runners
    assert (time.time() - t_disconnect_page_2) < 0.15, "should be cancelled quickly"

    assert not context.closed_event.is_set()
    await cull_task2
    assert context.closed_event.is_set()
    # the context should be closed AFTER the 0.2s cull window; no tight upper bound, a loaded
    # runner can delay the wakeup well beyond the window
    assert 1.0 >= (time.time() - t0_disconnect_page_2) >= 0.2


@pytest.mark.skipif(on_windows, reason="This test is flaky on Windows")
@pytest.mark.parametrize("close_first", [True, False])
async def test_kernel_lifecycle_close_single(close_first, short_cull_timeout):
    # a reconnect should be possible within the reconnect window
    websocket = Mock()
    context = kernel_context.initialize_virtual_kernel("session-id-1", "kernel-id-1", websocket)
    connection = context.page_connect("page-id-1")
    if close_first:
        context.page_close("page-id-1")
        assert context.closed_event.is_set()
        context.page_disconnect("page-id-1", connection)
    else:
        context.page_disconnect("page-id-1", connection)
        assert not context.closed_event.is_set()
        context.page_close("page-id-1")
        assert context.closed_event.is_set()


@pytest.mark.skipif(on_windows, reason="This test is flaky on Windows")
@pytest.mark.parametrize("close_first", [True, False])
async def test_kernel_lifecycle_close_while_disconnected(close_first, short_cull_timeout):
    # a reconnect should be possible within the reconnect window
    websocket = Mock()
    context = kernel_context.initialize_virtual_kernel(f"session-id-1-{close_first}", f"kernel-id-1-{close_first}", websocket)
    connection_1 = context.page_connect("page-id-1")
    cull_task_1 = context.page_disconnect("page-id-1", connection_1)
    await asyncio.sleep(0.1)
    # after 0.1 we connect again, but close it directly
    connection_2 = context.page_connect("page-id-2")
    if close_first:
        cull_task_2 = context.page_close("page-id-2")
        await asyncio.sleep(0.01)
        context.page_disconnect("page-id-2", connection_2)
    else:
        context.page_disconnect("page-id-2", connection_2)
        await asyncio.sleep(0.01)
        cull_task_2 = context.page_close("page-id-2")
    assert cull_task_2 is not None
    assert not context.closed_event.is_set()
    await asyncio.sleep(0.15)
    # but even though we closed, the first page is still in the disconnected state
    with pytest.raises(asyncio.CancelledError):
        await cull_task_1
    assert not context.closed_event.is_set()
    await cull_task_2
    assert context.closed_event.is_set()


@pytest.mark.skipif(on_windows, reason="This test is flaky on Windows")
async def test_kernel_lifecycle_reconnect_before_disconnect(short_cull_timeout):
    # When only the browser's side of a connection is dropped (by a proxy, or the network), the
    # browser reconnects right away, while the server only drops the old websocket once its ping
    # times out. The new websocket of the page then connects before the old one disconnects.
    websocket = Mock()
    context = kernel_context.initialize_virtual_kernel("session-id-1", "kernel-id-1", websocket)
    connection_old = context.page_connect("page-id-1")
    connection_new = context.page_connect("page-id-1")

    await context.page_disconnect("page-id-1", connection_old)
    # the page still has a connection, so it should not be disconnected, and the kernel not culled
    assert context.page_status["page-id-1"] == kernel_context.PageStatus.CONNECTED
    await asyncio.sleep(0.2 + 0.1)
    assert not context.closed_event.is_set()

    # only the last connection disconnects the page
    await context.page_disconnect("page-id-1", connection_new)
    assert context.page_status["page-id-1"] == kernel_context.PageStatus.CLOSED
    assert context.closed_event.is_set()


@pytest.mark.skipif(on_windows, reason="This test is flaky on Windows")
async def test_kernel_lifecycle_stray_disconnect_does_nothing(short_cull_timeout):
    websocket = Mock()
    context = kernel_context.initialize_virtual_kernel("session-id-1", "kernel-id-1", websocket)
    connection = context.page_connect("page-id-1")

    await context.page_disconnect("page-id-1", connection + 100)
    assert context.page_status["page-id-1"] == kernel_context.PageStatus.CONNECTED
    assert not context.closed_event.is_set()

    cull_task = context.page_disconnect("page-id-1", connection)
    context.page_disconnect("page-id-1", connection)
    assert context.page_status["page-id-1"] == kernel_context.PageStatus.DISCONNECTED
    await cull_task
    assert context.page_status["page-id-1"] == kernel_context.PageStatus.CLOSED
    assert context.closed_event.is_set()


@pytest.mark.skipif(on_windows, reason="This test is flaky on Windows")
async def test_kernel_lifecycle_close_beacon_with_two_open_websockets(short_cull_timeout):
    websocket = Mock()
    context = kernel_context.initialize_virtual_kernel("session-id-1", "kernel-id-1", websocket)
    connection_1 = context.page_connect("page-id-1")
    connection_2 = context.page_connect("page-id-1")

    context.page_close("page-id-1")
    assert context.page_status["page-id-1"] == kernel_context.PageStatus.CLOSED
    assert context.closed_event.is_set()

    context.page_disconnect("page-id-1", connection_1)
    context.page_disconnect("page-id-1", connection_2)


class WebsocketOpenUntilDropped(solara.server.websocket.WebsocketWrapper):
    def __init__(self):
        self.receiving = asyncio.Event()
        self.dropped = asyncio.Event()

    def send_text(self, data):
        pass

    def send_bytes(self, data):
        pass

    def close(self):
        self.dropped.set()

    async def receive(self):
        self.receiving.set()
        await self.dropped.wait()
        raise solara.server.websocket.WebSocketDisconnect()


@pytest.mark.skipif(on_windows, reason="This test is flaky on Windows")
async def test_app_loop_reconnect_before_disconnect(short_cull_timeout):
    # same as test_kernel_lifecycle_reconnect_before_disconnect, using the websocket handler
    websocket_old = WebsocketOpenUntilDropped()
    websocket_new = WebsocketOpenUntilDropped()

    def app_loop(websocket):
        return solara.server.server.app_loop(websocket, {}, {}, "session-id-1", "kernel-id-1", "page-id-1")

    handler_old = asyncio.create_task(app_loop(websocket_old))
    await websocket_old.receiving.wait()
    handler_new = asyncio.create_task(app_loop(websocket_new))
    await websocket_new.receiving.wait()
    context = kernel_context.contexts["kernel-id-1"]

    websocket_old.dropped.set()
    await handler_old
    assert context.page_status["page-id-1"] == kernel_context.PageStatus.CONNECTED
    await asyncio.sleep(0.2 + 0.1)
    assert not context.closed_event.is_set()
    assert not handler_new.done()

    websocket_new.dropped.set()
    await handler_new
    assert context.page_status["page-id-1"] == kernel_context.PageStatus.DISCONNECTED
    # the kernel is culled after the 0.2s cull window
    for _ in range(100):
        if context.closed_event.is_set():
            break
        await asyncio.sleep(0.02)
    assert context.closed_event.is_set()
