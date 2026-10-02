import websockets
import websockets.http11

import solara.server.starlette  # noqa: F401


def test_websocket_handshake_accepts_large_cookies():
    # uvicorn 0.54+ lets websockets' sans-I/O code parse the handshake, so a browser with more than
    # 8kb of cookies can only connect when solara raised the limit there too
    if int(websockets.__version__.split(".")[0]) >= 13:
        assert websockets.http11.MAX_LINE_LENGTH >= 1024 * 32
    else:
        assert websockets.http11.MAX_LINE >= 1024 * 32
