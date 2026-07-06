"""Synchronous websocket frame writing for the kernel connection.

The default send path schedules every websocket message on the event loop
(``portal.call`` per message from the render thread): a thread handoff, a task,
and a loop wakeup per message. A page render sends hundreds of messages, so on
a small instance this machinery costs more than building and serializing the
widgets themselves (measured: dropping it halves the server-side render wall).

With ``SOLARA_SERVER_SYNC_WS_WRITE=true`` frames are written synchronously from
whatever thread sends them:

- ``write_frame_sync`` on uvicorn's websockets protocol object is the single
  funnel for every post-handshake frame (data, ping/pong, close — see
  ``websockets.legacy.protocol``), and it already applies negotiated extensions
  (permessage-deflate) via ``Frame.write``. We replace it *per connection* with
  a version that serializes frame construction under a lock and writes to the
  socket file descriptor with a blocking retry loop, instead of
  ``transport.write``.
- Because the loop's own control frames also go through the same (patched)
  funnel, data and control frames cannot interleave mid-frame, and the deflate
  context stays single-threaded under the lock.
- The asyncio transport is no longer handed bytes after the patch; reading
  stays fully on the event loop, untouched.
- Backpressure is the OS socket buffer: a slow client blocks the sending
  (render) thread instead of growing an unbounded queue.

Requirements and fallbacks (checked per connection, falling back to the
default path with one log message):

- uvicorn must use the ``websockets`` implementation (the default when
  installed; not ``wsproto``).
- plain TCP transport (no TLS terminated in uvicorn itself — writing the raw
  fd would bypass the SSL layer; TLS-terminating proxies in front are fine).
"""

import errno
import logging
import os
import socket
import threading
import time
from typing import Any, Callable, Optional

logger = logging.getLogger("solara.server.sync_ws_write")

_unavailable_logged = False


def _log_unavailable_once(reason: str) -> None:
    global _unavailable_logged
    if not _unavailable_logged:
        _unavailable_logged = True
        logger.warning("sync_ws_write requested but unavailable (%s), using the default send path", reason)


def _find_websockets_protocol(send: Optional[Callable], depth: int = 0) -> Optional[Any]:
    """The uvicorn protocol object, unwrapped from starlette's middleware closures.

    starlette wraps the raw ASGI ``send`` (a bound method of uvicorn's
    ``WebSocketProtocol``) in plain function closures; walk them.
    """
    try:
        from websockets.legacy.protocol import WebSocketCommonProtocol
    except ImportError:
        return None
    if depth > 10 or send is None:
        return None
    self_ = getattr(send, "__self__", None)
    if isinstance(self_, WebSocketCommonProtocol):
        return self_
    for cell in getattr(send, "__closure__", None) or ():
        value = cell.cell_contents
        if callable(value):
            found = _find_websockets_protocol(value, depth + 1)
            if found is not None:
                return found
    return None


class SyncFrameWriter:
    """Owns all frame writes of one websocket connection, synchronously."""

    def __init__(self, protocol: Any, sock_fd: int) -> None:
        from websockets.frames import Opcode
        from websockets.legacy.framing import Frame

        self._Frame = Frame
        self._OP_TEXT = Opcode.TEXT
        self._OP_BINARY = Opcode.BINARY
        self.protocol = protocol
        self.fd = sock_fd
        self.lock = threading.Lock()
        # every frame the protocol writes from now on (ping/pong/close included)
        # goes through us: single writer, no transport.write interleaving
        protocol.write_frame_sync = self._write_frame_sync

    @classmethod
    def try_create(cls, ws: Any) -> Optional["SyncFrameWriter"]:
        """ws is a starlette WebSocket; returns None (with one log) when unsupported."""
        if os.name != "posix":
            # os.write on a socket fileno is POSIX-only (Windows sockets are
            # WSA handles, not CRT file descriptors)
            _log_unavailable_once("synchronous socket writes require POSIX")
            return None
        protocol = _find_websockets_protocol(getattr(ws, "_send", None))
        if protocol is None:
            _log_unavailable_once("uvicorn websockets protocol not found; wsproto or unknown server?")
            return None
        transport = getattr(protocol, "transport", None)
        if transport is None:
            _log_unavailable_once("protocol has no transport")
            return None
        if transport.get_extra_info("ssl_object") is not None:
            _log_unavailable_once("TLS is terminated in-process; raw fd writes would bypass it")
            return None
        sock: Optional[socket.socket] = transport.get_extra_info("socket")
        if sock is None:
            _log_unavailable_once("transport exposes no socket")
            return None
        if transport.get_write_buffer_size() > 0:
            # pending asyncio-buffered bytes (handshake tail) would reorder with
            # our direct writes; extremely unlikely at kernel-connect time
            _log_unavailable_once("transport write buffer not empty at connection setup")
            return None
        logger.info("sync_ws_write active for this connection")
        return cls(protocol, sock.fileno())

    # -- the funnel (replaces protocol.write_frame_sync, same signature) --------
    def _write_frame_sync(self, fin: bool, opcode: int, data: bytes) -> None:
        frame = self._Frame(fin, opcode, data)
        with self.lock:
            frame.write(self._os_write, mask=self.protocol.is_client, extensions=self.protocol.extensions)

    def _os_write(self, data: bytes) -> None:
        view = memoryview(data)
        while view:
            try:
                n = os.write(self.fd, view)
                view = view[n:]
            except BlockingIOError as e:
                if e.errno not in (errno.EAGAIN, errno.EWOULDBLOCK):
                    raise
                # socket buffer full: block the sending thread briefly
                # (backpressure), not the event loop
                time.sleep(0.0005)
            except InterruptedError:
                continue

    # -- used by WebsocketWrapper.send_text/send_bytes ---------------------------
    def send_text(self, data: str) -> None:
        self._write_frame_sync(True, self._OP_TEXT, data.encode())

    def send_bytes(self, data: bytes) -> None:
        self._write_frame_sync(True, self._OP_BINARY, data)
