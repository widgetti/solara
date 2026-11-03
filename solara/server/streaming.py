import asyncio
import secrets
import threading
import time
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import AsyncGenerator, Callable, Dict, Optional, Set, Tuple

from . import kernel_context, settings

_PATH = "/_solara/api/streams"
_TTL = 60.0
_LIMIT = 8
_lock = threading.Lock()
_streams: Dict[str, "_Stream"] = {}
_connection_owner: "ContextVar[Optional[_Owner]]" = ContextVar("stream_connection_owner", default=None)


def _principal(user: Optional[dict]) -> Tuple[bool, Optional[Tuple[str, str, str]]]:
    if user is None:
        return False, None
    info = user.get("userinfo")
    subject = info.get("sub") if isinstance(info, dict) else None
    if not isinstance(subject, str) or not subject.strip():
        return True, None
    return True, (settings.oauth.api_base_url, settings.oauth.client_id, subject)


@dataclass
class _Owner:
    root_path: str
    principal: Tuple[bool, Optional[Tuple[str, str, str]]]
    tokens: Set[str] = field(default_factory=set)


@dataclass
class _Stream:
    context: "kernel_context.VirtualKernelContext"
    owner: _Owner
    factory: Callable[[], AsyncGenerator[bytes, None]]
    media_type: str
    expires: float
    timer: Optional[asyncio.TimerHandle] = None
    cancel: Optional[Callable[[], None]] = None


def _forget(token: str) -> Optional[_Stream]:
    stream = _streams.pop(token, None)
    if stream is not None:
        stream.owner.tokens.remove(token)
        if stream.timer is not None:
            kernel_context.keep_alive_event_loop.call_soon_threadsafe(stream.timer.cancel)
    return stream


def _expire(token: str) -> None:
    with _lock:
        stream = _streams.get(token)
        if stream is not None and stream.cancel is None:
            stream.timer = None
            _forget(token)


def _schedule_expiry(token: str) -> None:
    with _lock:
        stream = _streams.get(token)
        if stream is not None and stream.cancel is None:
            stream.timer = kernel_context.keep_alive_event_loop.call_later(max(0.0, stream.expires - time.monotonic()), _expire, token)


def _revoke(owner: _Owner) -> None:
    for token in list(owner.tokens):
        stream = _forget(token)
        if stream is not None and stream.cancel is not None:
            stream.cancel()


def _configure(context: "kernel_context.VirtualKernelContext", root_path: str, user: Optional[dict]) -> Optional[_Owner]:
    principal = _principal(user)
    with _lock:
        if context._teardown_done or context.closed_event.is_set():
            return None
        owner = context._stream_owner
        if owner is not None and (owner.root_path != root_path or owner.principal != principal):
            _revoke(owner)
            owner = None
        if owner is None:
            owner = context._stream_owner = _Owner(root_path, principal)
        return owner


def _clear(context: "kernel_context.VirtualKernelContext", closing: bool = False) -> None:
    with _lock:
        owner = context._stream_owner
        if owner is not None:
            _revoke(owner)
        if closing:
            context._stream_owner = None


def _authorized(principal: Tuple[bool, Optional[Tuple[str, str, str]]]) -> bool:
    authenticated, identity = principal
    return identity is not None if authenticated else not settings.oauth.private


def register_stream(factory: Callable[[], AsyncGenerator[bytes, None]], *, media_type: str = "application/octet-stream") -> str:
    """Register a single-use binary stream from a live Starlette or FastAPI kernel callback.

    The owning browser session gets a same-origin URL. An authorized GET starts
    the async generator factory on the HTTP event loop with the kernel context
    available to the generator and its async child tasks until the stream ends.
    Open loop-bound upstream clients inside the generator and close
    them in an async context manager or finally block. The generator must
    cooperate with cancellation. Keep widget updates on the kernel connection.

    Claim the URL within 60 seconds. Register a fresh URL for each playback or
    retry. The kernel can hold eight pending and active streams combined.
    Registration raises RuntimeError outside a supported live kernel or when
    that limit is reached. Kernel close and restart revoke outstanding URLs and
    cancel active streams.

    Route the GET and kernel websocket to the same worker. Registrations are
    process-local and do not survive worker loss. Use a streaming-capable proxy.
    Treat the URL as a credential within the session and redact it from access logs.
    """
    if not media_type or any(not 32 <= ord(char) <= 126 for char in media_type):
        raise ValueError("Expected a printable ASCII media type")
    context = kernel_context.get_current_context()
    with _lock:
        owner = context._stream_owner
        if owner is None or context._teardown_done or kernel_context.contexts.get(context.id) is not context:
            raise RuntimeError("Streaming requires a live Starlette or FastAPI kernel")
        if owner is not _connection_owner.get() or not _authorized(owner.principal):
            raise RuntimeError("Streaming requires a stable authenticated identity")
        root_path = owner.root_path.rstrip("/")
        if root_path and (
            not root_path.startswith("/")
            or root_path.startswith("//")
            or any(char in root_path for char in "\\?#")
            or any(char.isspace() for char in root_path)
        ):
            raise RuntimeError("Streaming requires a same-origin Solara root path")
        if len(owner.tokens) >= _LIMIT:
            raise RuntimeError("Kernel stream limit reached")
        token = secrets.token_urlsafe(32)
        _streams[token] = _Stream(context, owner, factory, media_type, time.monotonic() + _TTL)
        owner.tokens.add(token)
        kernel_context.keep_alive_event_loop.call_soon_threadsafe(_schedule_expiry, token)
    return f"{root_path}{_PATH}/{token}"


def _claim(token: str, session_id: Optional[str], user: Optional[dict], cancel: Callable[[], None]) -> Optional[_Stream]:
    principal = _principal(user)
    with _lock:
        stream = _streams.get(token)
        if stream is None or stream.cancel is not None:
            return None
        if stream.expires <= time.monotonic():
            _forget(token)
            return None
        context = stream.context
        if (
            not session_id
            or session_id != context.session_id
            or kernel_context.contexts.get(context.id) is not context
            or context._teardown_done
            or stream.owner.principal != principal
            or not _authorized(principal)
        ):
            return None
        stream.cancel = cancel
        if stream.timer is not None:
            kernel_context.keep_alive_event_loop.call_soon_threadsafe(stream.timer.cancel)
            stream.timer = None
        return stream


def _live(token: str, stream: _Stream) -> bool:
    with _lock:
        context = stream.context
        return _streams.get(token) is stream and not context._teardown_done and kernel_context.contexts.get(context.id) is context


def _release(token: str) -> None:
    with _lock:
        _forget(token)
