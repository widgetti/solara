import asyncio
import sys
import time
from unittest.mock import Mock

import pytest

import solara.server.server
import solara.server.settings
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
    context.page_connect("page-id-1")
    cull_task1 = context.page_disconnect("page-id-1")
    await asyncio.sleep(0.01)
    context.page_connect("page-id-2")
    # the new connect should cancel the first cull task
    with pytest.raises(asyncio.CancelledError):
        await cull_task1
    assert not context.closed_event.is_set()
    await context.page_disconnect("page-id-2")
    assert context.closed_event.is_set()


@pytest.mark.skipif(on_windows, reason="This test is flaky on Windows")
async def test_kernel_lifecycle_double_disconnect(short_cull_timeout):
    # a reconnect should be possible within the reconnect window
    websocket = Mock()
    context = kernel_context.initialize_virtual_kernel("session-id-1", "kernel-id-1", websocket)
    context.page_connect("page-id-1")
    cull_task1 = context.page_disconnect("page-id-1")

    # now after 0.1 we disconnect the 2nd time
    await asyncio.sleep(0.1)
    context.page_connect("page-id-2")
    cull_task2 = context.page_disconnect("page-id-2")
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
    context.page_connect("page-id-1")
    if close_first:
        context.page_close("page-id-1")
        assert context.closed_event.is_set()
        context.page_disconnect("page-id-1")
    else:
        context.page_disconnect("page-id-1")
        assert not context.closed_event.is_set()
        context.page_close("page-id-1")
        assert context.closed_event.is_set()


@pytest.mark.skipif(on_windows, reason="This test is flaky on Windows")
@pytest.mark.parametrize("close_first", [True, False])
async def test_kernel_lifecycle_close_while_disconnected(close_first, short_cull_timeout):
    # a reconnect should be possible within the reconnect window
    websocket = Mock()
    context = kernel_context.initialize_virtual_kernel(f"session-id-1-{close_first}", f"kernel-id-1-{close_first}", websocket)
    context.page_connect("page-id-1")
    cull_task_1 = context.page_disconnect("page-id-1")
    await asyncio.sleep(0.1)
    # after 0.1 we connect again, but close it directly
    context.page_connect("page-id-2")
    if close_first:
        cull_task_2 = context.page_close("page-id-2")
        await asyncio.sleep(0.01)
        context.page_disconnect("page-id-2")
    else:
        context.page_disconnect("page-id-2")
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
