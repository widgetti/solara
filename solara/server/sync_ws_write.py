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
- The event loop never waits for a write. It writes its own frames (pings,
  pongs, close) as far as the socket takes them when no other thread writes;
  a short-lived thread writes the rest, and the protocol's drain waits for it.
  Frames sent from the event loop wait in a queue while a client is slow, as
  they do on the default send path. A close frame that websockets writes
  without a drain (``fail_connection``, server shutdown, a close from both
  sides at once) is lost when a thread is writing to that client at that
  moment; the client then sees code 1006 (solara's kernel client ignores the
  code and reconnects on every close).
- We write to our own duplicate of the socket fd and end the connection
  ourselves when it is lost. A thread that still writes when asyncio closes its
  fd can never write into the socket or file that gets that fd number next.

Requirements and fallbacks (checked per connection, falling back to the
default path with one log message):

- uvicorn must use the ``websockets`` implementation (the default when
  installed; not ``wsproto``).
- plain TCP transport (no TLS terminated in uvicorn itself — writing the raw
  fd would bypass the SSL layer; TLS-terminating proxies in front are fine).
"""

import _thread
import asyncio
import collections
import errno
import logging
import os
import socket
import threading
import time
from typing import Any, Callable, Deque, List, Optional, Tuple

logger = logging.getLogger("solara.server.sync_ws_write")

_unavailable_logged = False

# what we read from or replace on the protocol object (websockets.legacy 10 to 16 have them)
_PROTOCOL_ATTRIBUTES = ("loop", "connection_lost_waiter", "_drain", "is_client", "extensions")


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


def _set_done(future: "asyncio.Future[None]") -> None:
    if not future.done():
        future.set_result(None)


def _start_thread(target: Callable, *args: Any) -> None:
    # not threading.Thread: its start() waits until the new thread runs, and on the
    # event loop that takes many ms while render threads keep the GIL busy
    _thread.start_new_thread(target, args)


class SyncFrameWriter:
    """Owns all frame writes of one websocket connection, synchronously."""

    def __init__(self, protocol: Any, sock: Any) -> None:
        from websockets.frames import Opcode
        from websockets.legacy.framing import Frame

        self._Frame = Frame
        self._OP_TEXT = Opcode.TEXT
        self._OP_BINARY = Opcode.BINARY
        self.protocol = protocol
        # Our own fd for the socket. asyncio closes its fd when the connection ends,
        # and the OS gives that number to the next socket or file this process opens.
        # A thread that still writes to the old number would write into that one.
        # Ours stays valid until we close it, under the lock (see _on_connection_lost).
        self._sock = socket.socket(fileno=os.dup(sock.fileno()))
        self.fd = self._sock.fileno()
        # Whoever holds the lock writes to the socket. It first writes what the event
        # loop left (_write_pending_locked), so frames go out in the order they were sent.
        self.lock = threading.Lock()
        # we are created on the event loop thread; see _write_frame_sync
        self._loop = protocol.loop
        self._loop_thread_id = threading.get_ident()
        # What the event loop left: the rest of a frame it started (only touched under
        # self.lock), then the frames it could not start (under _loop_frames_lock; only
        # the loop holds it during a write, and that write never waits).
        self._rest: Optional[bytes] = None
        self._loop_frames: Deque[Tuple[bool, int, bytes]] = collections.deque()
        self._loop_frames_lock = threading.Lock()
        # Set while the loop left something, done when a thread wrote it all. While it is
        # set, the loop queues its frames, so they cannot overtake what it left.
        self._loop_frames_written: Optional["asyncio.Future[None]"] = None
        self._protocol_drain = protocol._drain
        # every frame the protocol writes from now on (ping/pong/close included)
        # goes through us: single writer, no transport.write interleaving
        protocol.write_frame_sync = self._write_frame_sync
        protocol._drain = self._drain
        protocol.connection_lost_waiter.add_done_callback(self._on_connection_lost)

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
        missing = [name for name in _PROTOCOL_ATTRIBUTES if not hasattr(protocol, name)]
        if missing:
            _log_unavailable_once(f"websockets protocol has no {', '.join(missing)}")
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
        try:
            writer = cls(protocol, sock)
        except OSError as e:  # os.dup: no free fd; nothing is patched yet
            _log_unavailable_once(f"could not duplicate the socket fd: {e}")
            return None
        logger.info("sync_ws_write active for this connection")
        return writer

    # -- the funnel (replaces protocol.write_frame_sync, same signature) --------
    def _write_frame_sync(self, fin: bool, opcode: int, data: bytes) -> None:
        if threading.get_ident() != self._loop_thread_id:
            self._write_frame(fin, opcode, data)
            return
        # The event loop serves every connection of this process, so it must never
        # wait for one slow client: not on the lock (a render thread holds it while
        # the client's socket is full) and not on a full socket itself. When nobody
        # writes and it left nothing, it writes the frame as far as the socket takes
        # it. A short-lived thread writes the rest, or the whole frame when the lock
        # is taken, and the protocol's drain waits for that thread (see _drain).
        with self._loop_frames_lock:
            if self._loop_frames_written is None and self.lock.acquire(blocking=False):
                try:
                    rest = self._rest = self._write_now_locked(self._Frame(fin, opcode, data))
                finally:
                    self.lock.release()
                if rest is None:
                    return
            else:
                self._loop_frames.append((fin, opcode, data))
                if self._loop_frames_written is not None:
                    return  # the running thread writes this one too
            written = self._loop_frames_written = self._loop.create_future()
        try:
            _start_thread(self._write_loop_frames, written)
        except RuntimeError:  # no thread left: write here, the loop waits as it did before
            logger.exception("could not start a thread to write websocket frames")
            self._write_loop_frames(written)

    def _write_now_locked(self, frame: Any) -> Optional[bytes]:
        """Write a frame as far as the socket takes it without waiting, and return the rest."""
        chunks: List[bytes] = []
        frame.write(chunks.append, mask=self.protocol.is_client, extensions=self.protocol.extensions)
        view = memoryview(b"".join(chunks))
        while view:
            try:
                n = os.write(self.fd, view)
            except InterruptedError:
                continue
            except BlockingIOError:
                return bytes(view)
            except OSError:
                return None  # the connection is gone; the protocol finds out on its own
            view = view[n:]
        return None

    def _write_loop_frames(self, written: "asyncio.Future[None]") -> None:
        with self.lock:
            while True:
                try:
                    self._write_pending_locked()
                except Exception as e:
                    if not isinstance(e, OSError):  # an OSError: the connection is gone
                        logger.exception("could not write a websocket frame from the event loop")
                    self._rest = None
                    with self._loop_frames_lock:
                        self._loop_frames.clear()
                with self._loop_frames_lock:
                    if not self._loop_frames:
                        self._loop_frames_written = None
                        break
        try:
            self._loop.call_soon_threadsafe(_set_done, written)
        except RuntimeError:
            pass  # the event loop is closed

    def _write_pending_locked(self) -> None:
        """Write what the event loop left, in order; the caller holds self.lock."""
        if self._rest is not None:
            rest, self._rest = self._rest, None
            self._os_write(rest)
        while True:
            with self._loop_frames_lock:
                if not self._loop_frames:
                    return
                fin, opcode, data = self._loop_frames.popleft()
            self._Frame(fin, opcode, data).write(self._os_write, mask=self.protocol.is_client, extensions=self.protocol.extensions)

    # -- replaces protocol._drain ------------------------------------------------
    async def _drain(self) -> None:
        # The protocol drains after each frame it writes, and after the drain of its
        # close frame it closes the TCP connection. Wait until our thread wrote the
        # loop's frames, so that the close frame goes out before the connection ends.
        written = self._loop_frames_written
        if written is not None:
            await asyncio.shield(written)
        await self._protocol_drain()

    # -- called on the event loop when the connection is lost --------------------
    def _on_connection_lost(self, _: Any) -> None:
        # asyncio closed its fd, but ours keeps the TCP connection open: end it.
        # A thread that waits on a full socket then fails at once (EPIPE).
        try:
            self._sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass  # already ended
        # Close our fd only while nobody writes to it. The event loop must not wait
        # for the lock, so when a thread holds it, another thread waits for it.
        if self.lock.acquire(blocking=False):
            try:
                self._close_fd_locked()
            finally:
                self.lock.release()
        else:
            try:
                _start_thread(self._close_fd)
            except RuntimeError:
                pass  # no thread left: the fd closes when this writer is garbage collected

    def _close_fd(self) -> None:
        with self.lock:
            self._close_fd_locked()

    def _close_fd_locked(self) -> None:
        self._sock.close()
        self.fd = -1  # os.write fails with EBADF from now on, and -1 is never reused

    def _write_frame(self, fin: bool, opcode: int, data: bytes) -> None:
        frame = self._Frame(fin, opcode, data)
        with self.lock:
            self._write_pending_locked()  # what the event loop sent before us goes first
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
