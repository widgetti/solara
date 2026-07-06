"""SyncFrameWriter: correct RFC6455 frames, single-writer locking, protocol funnel."""

import socket
import threading

import pytest

websockets = pytest.importorskip("websockets")

from solara.server.sync_ws_write import SyncFrameWriter, _find_websockets_protocol  # noqa: E402


class FakeProtocol:
    """Just enough of websockets.legacy.protocol for the writer: no extensions."""

    is_client = False
    extensions: list = []

    def write_frame_sync(self, fin, opcode, data):  # replaced by the writer
        raise AssertionError("should have been patched")


def recv_frame(sock: socket.socket):
    header = sock.recv(2)
    fin = bool(header[0] & 0x80)
    opcode = header[0] & 0x0F
    length = header[1] & 0x7F
    if length == 126:
        length = int.from_bytes(sock.recv(2), "big")
    elif length == 127:
        length = int.from_bytes(sock.recv(8), "big")
    payload = b""
    while len(payload) < length:
        payload += sock.recv(length - len(payload))
    return fin, opcode, payload


@pytest.fixture()
def writer_and_peer():
    server_sock, client_sock = socket.socketpair()
    protocol = FakeProtocol()
    writer = SyncFrameWriter(protocol, server_sock.fileno())
    yield writer, protocol, client_sock
    server_sock.close()
    client_sock.close()


def test_text_and_binary_frames(writer_and_peer):
    writer, _, peer = writer_and_peer
    writer.send_text("hello sync")
    fin, opcode, payload = recv_frame(peer)
    assert (fin, opcode, payload) == (True, 0x1, b"hello sync")

    writer.send_bytes(b"\x00\x01binary")
    fin, opcode, payload = recv_frame(peer)
    assert (fin, opcode, payload) == (True, 0x2, b"\x00\x01binary")


def test_large_frame_survives_partial_writes(writer_and_peer):
    writer, _, peer = writer_and_peer
    big = "x" * 300_000  # larger than default socketpair buffers -> EAGAIN path

    received = {}

    def drain():
        received["frame"] = recv_frame(peer)

    t = threading.Thread(target=drain)
    t.start()
    writer.send_text(big)
    t.join(timeout=10)
    fin, opcode, payload = received["frame"]
    assert fin and opcode == 0x1
    assert payload == big.encode()


def test_protocol_control_frames_share_the_funnel(writer_and_peer):
    """ping/close written by the protocol go through the same patched writer."""
    writer, protocol, peer = writer_and_peer
    protocol.write_frame_sync(True, 0x9, b"ping-payload")  # as the loop would
    fin, opcode, payload = recv_frame(peer)
    assert (fin, opcode, payload) == (True, 0x9, b"ping-payload")


def test_find_protocol_unwraps_closures():
    from websockets.legacy.protocol import WebSocketCommonProtocol

    class P(WebSocketCommonProtocol):
        def __init__(self):  # skip the real (loop-requiring) init
            pass

    protocol = P()

    async def asgi_send(msg):  # bound-method stand-in
        pass

    bound = protocol.connection_lost.__get__(protocol)  # any bound method of P

    def middleware_wrap(send):
        async def sender(message):
            await send(message)

        return sender

    wrapped = middleware_wrap(middleware_wrap(bound))
    assert _find_websockets_protocol(wrapped) is protocol
    assert _find_websockets_protocol(middleware_wrap(asgi_send)) is None
