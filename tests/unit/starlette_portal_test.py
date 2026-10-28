import asyncio
import concurrent.futures
import logging
from typing import Any, cast

import anyio.from_thread
import pytest

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
