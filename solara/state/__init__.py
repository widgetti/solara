"""Core state-persistence layer: signed envelopes, the backend contract, and the registry.

This is the (no-Redis, no-server-changes) core of the opt-in reactive state persistence
feature. Commit 2 wires the server lifecycle (takeover on connect, write-behind flush),
commit 3 adds the Redis backend, commit 4 the client soft-remount.
"""

from typing import Dict, Optional

import solara.settings
import solara.util

from .backend import StateBackend, TakeoverResult
from .memory import MemoryStateBackend
from .envelope import (
    CodecError,
    EnvelopeError,
    HmacError,
    SerializeError,
    decode,
    encode,
    register_codec,
    session_hmac,
)

try:
    from . import derive  # noqa: F401  (created by a parallel commit; optional here)
except ImportError:
    pass

__all__ = [
    "StateBackend",
    "TakeoverResult",
    "MemoryStateBackend",
    "state_backend_map",
    "get_backend",
    "reset_backend",
    "validate_state_settings",
    "encode",
    "decode",
    "register_codec",
    "session_hmac",
    "EnvelopeError",
    "HmacError",
    "CodecError",
    "SerializeError",
]

# name -> dotted class path, resolved lazily (like solara.cache.cache_type_map); the redis
# path is imported only when actually selected, so `redis` stays an optional dependency.
state_backend_map: Dict[str, str] = {
    "memory": "solara.state.memory.MemoryStateBackend",
    "redis": "solara.state.redis.RedisStateBackend",
}

_backend: Optional[StateBackend] = None
_backend_built = False


def get_backend() -> Optional[StateBackend]:
    """Return the process-wide state backend singleton, or None when persistence is disabled."""
    global _backend, _backend_built
    if _backend_built:
        return _backend
    name = solara.settings.state.backend
    if not name:
        _backend = None
    elif name not in state_backend_map:
        raise ValueError(f"Unknown state backend {name!r}; known: {sorted(state_backend_map)}")
    else:
        cls = solara.util.import_item(state_backend_map[name])
        _backend = cls()
    _backend_built = True
    return _backend


def reset_backend() -> None:
    """Drop the cached backend singleton (test hook / re-read settings)."""
    global _backend, _backend_built
    _backend = None
    _backend_built = False


def validate_state_settings() -> None:
    """Validate state settings at server start. Raises ValueError on a misconfiguration.

    - pickle codec enabled with empty/default secrets is refused (even without a backend).
    - when a backend is configured, secret keys must be non-empty and not the placeholder,
      and the backend name must be known.
    """
    st = solara.settings.state
    keys = st.secret_key_list()
    default_or_empty = (not keys) or any(key == "change me" for key in keys)
    if st.allow_pickle and default_or_empty:
        raise ValueError("SOLARA_STATE_ALLOW_PICKLE=true requires real, non-default SOLARA_STATE_SECRET_KEYS to be set")
    if not st.backend:
        return
    if not keys:
        raise ValueError("SOLARA_STATE_SECRET_KEYS must be set (non-empty) when a state backend is enabled")
    if any(key == "change me" for key in keys):
        raise ValueError("SOLARA_STATE_SECRET_KEYS must not contain the placeholder value 'change me'")
    if st.backend not in state_backend_map:
        raise ValueError(f"Unknown state backend {st.backend!r}; known: {sorted(state_backend_map)}")
