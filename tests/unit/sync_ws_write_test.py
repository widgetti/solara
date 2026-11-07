"""SyncFrameWriter: correct RFC6455 frames, single-writer locking, protocol funnel."""

import asyncio
import os
import socket
import threading
import time
import unittest.mock

import pytest

websockets = pytest.importorskip("websockets")

from solara.server.sync_ws_write import SyncFrameWriter, _find_websockets_protocol  # noqa: E402

# the writer uses os.write on the socket fd: POSIX-only (and so is the feature;
# on Windows try_create falls back to the default send path)
fd_writes = pytest.mark.skipif(os.name != "posix", reason="os.write on sockets requires POSIX")

BIG = "x" * 2_000_000  # far more than the socket buffers hold


class FakeProtocol:
    """Just enough of websockets.legacy.protocol for the writer: no extensions."""

    is_client = False
    extensions: list = []

    def __init__(self, loop, sock):
        self.loop = loop
        self.sock = sock  # the socket asyncio owns
        self.connection_lost_waiter = loop.create_future()
        self.drained = 0

    def write_frame_sync(self, fin, opcode, data):  # replaced by the writer
        raise AssertionError("should have been patched")

    async def _drain(self):  # the writer waits for its own frames, then calls this one
        self.drained += 1

    def lose_connection(self):
        """What asyncio does: tell the protocol, close its fd, then run the callbacks."""
        self.connection_lost_waiter.set_result(None)
        self.sock.close()
        self.loop.run_until_complete(asyncio.sleep(0))


def in_thread(fn, *args):
    """Run fn as a render thread would (not on the loop thread); returns its exception."""
    result = {}

    def run():
        try:
            fn(*args)
        except Exception as e:
            result["exc"] = e

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return thread, result


def wait_until(condition, timeout=5.0):
    deadline = time.monotonic() + timeout
    while not condition():
        assert time.monotonic() < deadline, "timed out"
        time.sleep(0.001)


def render_blocks_on_a_full_socket(writer):
    """A render thread sends more than the socket holds, and keeps the lock while it waits."""
    render, result = in_thread(writer.send_text, BIG)
    wait_until(writer.lock.locked)
    return render, result


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
    loop = asyncio.new_event_loop()
    server_sock, client_sock = socket.socketpair()
    server_sock.setblocking(False)  # as asyncio has it
    client_sock.settimeout(10)  # a frame that never comes fails the test instead of hanging it
    protocol = FakeProtocol(loop, server_sock)
    writer = SyncFrameWriter(protocol, server_sock)  # made on this thread, which plays the event loop
    yield writer, protocol, client_sock
    if not protocol.connection_lost_waiter.done():
        protocol.lose_connection()
    client_sock.close()
    loop.close()


@fd_writes
def test_text_and_binary_frames(writer_and_peer):
    writer, _, peer = writer_and_peer
    writer.send_text("hello sync")
    fin, opcode, payload = recv_frame(peer)
    assert (fin, opcode, payload) == (True, 0x1, b"hello sync")

    writer.send_bytes(b"\x00\x01binary")
    fin, opcode, payload = recv_frame(peer)
    assert (fin, opcode, payload) == (True, 0x2, b"\x00\x01binary")


@fd_writes
def test_large_frame_survives_partial_writes(writer_and_peer):
    writer, _, peer = writer_and_peer
    render, result = in_thread(writer.send_text, BIG)  # more than the socket holds -> EAGAIN path
    frame = recv_frame(peer)
    render.join(timeout=10)
    assert "exc" not in result
    assert frame == (True, 0x1, BIG.encode())


@fd_writes
def test_a_frame_from_the_loop_does_not_wait_for_a_slow_client(writer_and_peer):
    """A client that stops reading must not stop the event loop: it serves every connection."""
    writer, protocol, peer = writer_and_peer
    render, _ = render_blocks_on_a_full_socket(writer)
    start = time.perf_counter()
    protocol.write_frame_sync(True, 0x9, b"ping-payload")  # the keepalive ping, as the loop sends it
    elapsed = time.perf_counter() - start
    assert elapsed < 0.5
    # both frames arrive whole once the client reads again, the data frame first
    frames = [recv_frame(peer), recv_frame(peer)]
    render.join(timeout=10)
    assert frames == [(True, 0x1, BIG.encode()), (True, 0x9, b"ping-payload")]


@fd_writes
def test_a_big_frame_from_the_loop_is_finished_by_a_thread(writer_and_peer):
    writer, protocol, peer = writer_and_peer
    start = time.perf_counter()
    protocol.write_frame_sync(True, 0x2, BIG.encode())  # the socket takes only a part
    assert time.perf_counter() - start < 0.5
    assert writer._loop_frames_written is not None  # a thread writes the rest
    render, _ = in_thread(writer.send_text, "after")
    frames = [recv_frame(peer), recv_frame(peer)]
    render.join(timeout=10)
    assert frames == [(True, 0x2, BIG.encode()), (True, 0x1, b"after")]


@fd_writes
def test_a_render_send_never_overtakes_a_frame_the_loop_queued(writer_and_peer):
    writer, protocol, peer = writer_and_peer
    with unittest.mock.patch.object(writer, "_write_loop_frames", lambda written: None):  # its thread is late
        with writer.lock:  # a render thread writes, so the loop has to queue
            protocol.write_frame_sync(True, 0x1, b"first")
        render, result = in_thread(writer.send_text, "second")
        render.join(timeout=5)
    assert "exc" not in result
    assert [recv_frame(peer), recv_frame(peer)] == [(True, 0x1, b"first"), (True, 0x1, b"second")]


@fd_writes
def test_the_loop_drain_waits_until_its_frames_are_written(writer_and_peer):
    """websockets ends the TCP connection right after it drained its close frame, so the frame must be out."""
    writer, protocol, peer = writer_and_peer
    render, _ = render_blocks_on_a_full_socket(writer)
    protocol.write_frame_sync(True, 0x8, b"\x03\xe8")  # the close frame, as the loop writes it: queued
    drain = protocol.loop.create_task(protocol._drain())
    protocol.loop.run_until_complete(asyncio.sleep(0.1))
    assert not drain.done()  # the client does not read, so the close frame is not written
    frames = [recv_frame(peer), recv_frame(peer)]  # the client reads again
    protocol.loop.run_until_complete(asyncio.wait_for(drain, timeout=10))
    assert writer._loop_frames_written is None
    assert protocol.drained == 1
    render.join(timeout=10)
    assert frames == [(True, 0x1, BIG.encode()), (True, 0x8, b"\x03\xe8")]


@fd_writes
def test_a_write_never_reaches_the_socket_that_reuses_the_fd_number(writer_and_peer):
    """When the connection ends, the OS gives its fd number to the next socket or file we open."""
    writer, protocol, peer = writer_and_peer
    render, result = render_blocks_on_a_full_socket(writer)
    other, other_peer = socket.socketpair()  # another user's connection, or a database socket
    # asyncio tells the protocol, closes its fd, and the OS gives the number to the
    # other socket (dup2 does the last two in one step), then the callbacks run
    number = protocol.sock.detach()
    protocol.connection_lost_waiter.set_result(None)
    os.dup2(other.fileno(), number)
    protocol.loop.run_until_complete(asyncio.sleep(0))
    render.join(timeout=5)
    other_peer.setblocking(False)
    with pytest.raises(BlockingIOError):
        other_peer.recv(1)  # not one byte of our frame
    assert not render.is_alive()
    assert isinstance(result.get("exc"), OSError)
    wait_until(lambda: writer.fd == -1)  # a thread closed our fd once the render thread let go of the lock
    os.close(number)
    other.close()
    other_peer.close()


@fd_writes
def test_writes_fail_after_the_connection_is_lost(writer_and_peer):
    writer, protocol, peer = writer_and_peer
    protocol.lose_connection()
    assert writer.fd == -1  # no thread wrote, so our fd closed at once
    render, result = in_thread(writer.send_text, "too late")
    render.join(timeout=5)
    assert isinstance(result.get("exc"), OSError)
    protocol.write_frame_sync(True, 0x9, b"ping-payload")  # the loop does not raise either


@fd_writes
def test_protocol_control_frames_share_the_funnel(writer_and_peer):
    """ping/close written by the protocol go through the same patched writer."""
    writer, protocol, peer = writer_and_peer
    protocol.write_frame_sync(True, 0x9, b"ping-payload")  # as the loop would
    assert writer._loop_frames_written is None  # written at once, no thread needed
    fin, opcode, payload = recv_frame(peer)
    assert (fin, opcode, payload) == (True, 0x9, b"ping-payload")


@fd_writes
@pytest.mark.parametrize("closer", ["client", "server", "server-fails"])
def test_close_codes_with_real_websockets_protocols(closer):
    """The writer patched into a real websockets.legacy protocol; the peer is a real one too."""
    from websockets.legacy.protocol import WebSocketCommonProtocol

    class Server(WebSocketCommonProtocol):
        is_client = False
        side = "server"

    class Client(WebSocketCommonProtocol):
        is_client = True
        side = "client"

    async def run():
        loop = asyncio.get_running_loop()
        server_sock, client_sock = socket.socketpair()
        server, client = Server(ping_interval=None), Client(ping_interval=None)
        server_transport, _ = await loop.create_connection(lambda: server, sock=server_sock)
        await loop.create_connection(lambda: client, sock=client_sock)
        server.connection_open()
        client.connection_open()
        writer = SyncFrameWriter(server, server_transport.get_extra_info("socket"))

        await loop.run_in_executor(None, writer.send_text, "from a render thread")
        assert await client.recv() == "from a render thread"
        if closer == "client":
            await client.close(code=1000)
            expected = 1000  # the server's reply
        elif closer == "server":
            await server.close(code=4001)
            expected = 4001
        else:
            server.fail_connection(1012)  # writes its close frame without a drain
            expected = 1012
        await client.wait_closed()
        await server.wait_closed()
        await asyncio.sleep(0)  # the connection-lost callbacks
        assert client.close_rcvd is not None and client.close_rcvd.code == expected
        assert writer.fd == -1

    asyncio.run(run())


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
