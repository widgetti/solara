import asyncio
import time
from unittest.mock import Mock

import pytest

import solara.server.server
import solara.server.settings
from solara.server import kernel_context


@pytest.fixture
def short_cull_timeout():
    cull_timeout_previous = solara.server.settings.kernel.cull_timeout
    solara.server.settings.kernel.cull_timeout = "0.2s"
    try:
        yield
    finally:
        solara.server.settings.kernel.cull_timeout = cull_timeout_previous


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
    assert (time.time() - t_disconnect_page_2) < 0.001, "should be cancelled really quickly"

    assert not context.closed_event.is_set()
    await cull_task2
    assert context.closed_event.is_set()
    # the context should be closed AFTER 0.2 seconds, but it could take a bit longer
    assert 0.3 >= (time.time() - t0_disconnect_page_2) >= 0.2


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


@pytest.mark.parametrize("close_first", [True, False])
async def test_kernel_lifecycle_close_while_disconnected(close_first, short_cull_timeout):
    # a reconnect should be possible within the reconnect window
    websocket = Mock()
    context = kernel_context.initialize_virtual_kernel("session-id-1", "kernel-id-1", websocket)
    context.page_connect("page-id-1")
    cull_task_1 = context.page_disconnect("page-id-1")
    await asyncio.sleep(0.1)
    # after 0.1 we connect again, but close it directly
    context.page_connect("page-id-2")
    if close_first:
        context.page_close("page-id-2")
        await asyncio.sleep(0.01)
        cull_task_2 = context.page_disconnect("page-id-2")
    else:
        cull_task_2 = context.page_disconnect("page-id-2")
        await asyncio.sleep(0.01)
        context.page_close("page-id-2")
    assert not context.closed_event.is_set()
    await asyncio.sleep(0.15)
    # but even though we closed, the first page is still in the disconnected state
    with pytest.raises(asyncio.CancelledError):
        await cull_task_1
    assert not context.closed_event.is_set()
    await cull_task_2
    assert context.closed_event.is_set()
