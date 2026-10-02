import os

import pytest

import solara.server.starlette  # noqa: F401


def test_websocket_handshake_accepts_large_cookies():
    # uvicorn 0.54+ lets websockets' sans-I/O code parse the handshake, so a browser with more than
    # 8kb of cookies can only connect when solara raised the limit there too
    if os.environ.get("WEBSOCKETS_MAX_LINE_LENGTH"):
        pytest.skip("the limit comes from WEBSOCKETS_MAX_LINE_LENGTH")
    websockets_server = pytest.importorskip("websockets.server")
    if not hasattr(websockets_server, "ServerProtocol"):
        pytest.skip("websockets < 11 has no ServerProtocol")
    from websockets.http11 import Request

    protocol = websockets_server.ServerProtocol()
    cookie = "; ".join(f"a_{i}={'a' * 1024}" for i in range(9))
    handshake = (
        "GET / HTTP/1.1\r\n"
        "Host: localhost\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\n"
        "Sec-WebSocket-Version: 13\r\n"
        f"Cookie: {cookie}\r\n"
        "\r\n"
    )
    protocol.receive_data(handshake.encode())
    events = protocol.events_received()
    assert len(events) == 1 and isinstance(events[0], Request), (events, protocol.handshake_exc)
