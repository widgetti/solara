import asyncio
import concurrent.futures
import gc
import logging
import weakref
from typing import Any, cast

import anyio.from_thread
import pytest
import starlette.websockets

from solara.server import kernel, websocket
from solara.server.starlette import WebsocketWrapper


def _wrapper_with_stopped_portal() -> WebsocketWrapper:
    # the websocket handler stops its portal when it exits
    with anyio.from_thread.start_blocking_portal() as portal:
        pass

    async def create():
        return WebsocketWrapper(cast(Any, None), portal)

    # like the server, create the wrapper on the event loop thread, and send from another thread
    with concurrent.futures.ThreadPoolExecutor(1) as executor:
        return executor.submit(asyncio.run, create()).result()


def test_send_and_close_after_portal_stopped_raise_disconnect():
    ws = _wrapper_with_stopped_portal()
    with pytest.raises(websocket.WebSocketDisconnect):
        ws.send_text("hi")
    with pytest.raises(websocket.WebSocketDisconnect):
        ws.send_bytes(b"hi")
    with pytest.raises(websocket.WebSocketDisconnect):
        ws.close()


def test_send_websockets_drops_websocket_with_stopped_portal_silently(caplog):
    # the close beacon can shut down the kernel while the websocket handler exits
    ws = _wrapper_with_stopped_portal()
    websockets = {cast(websocket.WebsocketWrapper, ws)}
    with caplog.at_level(logging.ERROR, logger="solara.server.kernel"):
        kernel.send_websockets(websockets, b"hi")
    assert websockets == set()
    assert caplog.records == []


class _FakeWebSocket:
    def __init__(self):
        self.sent: list = []

    async def send_text(self, data):
        self.sent.append(data)

    async def send_bytes(self, data):
        self.sent.append(data)


@pytest.mark.parametrize("data", ["hi", b"hi"], ids=["text", "bytes"])
def test_send_from_event_loop_thread_schedules_a_task(data):
    async def run():
        fake = _FakeWebSocket()
        async with anyio.from_thread.BlockingPortal() as portal:
            ws = WebsocketWrapper(cast(Any, fake), portal)
            send = ws.send_bytes if isinstance(data, bytes) else ws.send_text
            with pytest.warns(UserWarning, match="event loop thread"):
                send(data)
            await asyncio.gather(*ws.tasks)
        return fake.sent

    assert asyncio.run(run()) == [data]


class _DisconnectedWebSocket:
    async def send_text(self, data):
        raise starlette.websockets.WebSocketDisconnect()

    async def send_bytes(self, data):
        raise starlette.websockets.WebSocketDisconnect()

    async def close(self):
        raise starlette.websockets.WebSocketDisconnect()


class _HeldByTheCaller:
    pass


@pytest.mark.parametrize("operation", ["send_text", "send_bytes", "close"])
def test_disconnect_does_not_keep_the_callers_frames_alive(operation):
    # A kernel close sends comm-close messages to a websocket that is gone. The exception must not
    # form a reference cycle, or the traceback keeps the calling frames, and through them the render
    # context and the kernel context, alive until the cycle gc runs.
    args = {"send_text": ("hi",), "send_bytes": (b"hi",), "close": ()}[operation]

    async def create():
        return WebsocketWrapper(cast(Any, _DisconnectedWebSocket()), portal)

    def caller(held):
        try:
            getattr(ws, operation)(*args)
        except websocket.WebSocketDisconnect:
            return True
        return False

    with anyio.from_thread.start_blocking_portal() as portal:
        ws = portal.call(create)
        held = _HeldByTheCaller()
        held_ref = weakref.ref(held)
        gc.collect()
        gc.disable()
        try:
            assert caller(held)
            del held
            assert held_ref() is None
        finally:
            gc.enable()
