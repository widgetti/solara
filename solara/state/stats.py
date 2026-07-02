"""Process-global observability for state persistence (design §7a).

Two things live here:

- :class:`Stats` — a thread-safe singleton of process-wide counters and the last
  backend ok/error markers, with :meth:`Stats.as_dict` feeding the future ``/resourcez``
  ``state`` block (the server wiring in a follow-up commit reads it). The counters are the
  numbers §7a calls out: restore hit-ratio, flush failures, breaker transitions, and the
  broken-stickiness detectors (``superseded_*``).
- The structured log helpers (:func:`log_restore`, :func:`log_flush`, :func:`log_breaker`,
  :func:`log_close`) emitting the exact §7a line formats on the ``"solara.state"`` logger,
  one line per event at a fixed level, always carrying the kernel id. They only log;
  callers (the manager, the flush worker) bump the counters at the point the event happens.
"""

import logging
import threading
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger("solara.state")

# Per-key/per-kernel sync tables are capped: per-user key patterns (key=f"user:{id}:x") and
# long-lived processes would otherwise grow them unboundedly. Overflow aggregates into an
# "(other)" bucket and bumps the corresponding *_dropped counter.
SYNC_TABLE_CAP = 500
_OTHER = "(other)"

__all__ = [
    "Stats",
    "stats",
    "log_restore",
    "log_flush",
    "log_breaker",
    "log_close",
]


class Stats:
    """Process-wide state-persistence counters and last-backend markers (thread-safe)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # restore path (design §7a #3)
        self.restore_attempts = 0
        self.restore_success = 0
        self.restore_bailout = 0
        self.restore_miss = 0
        self.restore_schema_reset = 0
        # flush path (§7a #4)
        self.flush_ok = 0
        self.flush_rejected = 0
        self.flush_failures = 0
        # circuit breaker + supersession detectors (§7a #1, #5)
        self.breaker_transitions = 0
        self.superseded_closes = 0
        self.superseded_while_connected = 0
        # backend health (§7a #2); monotonic timestamp of the last acked backend write
        self.backend_last_ok: Optional[float] = None
        self.backend_last_error: Optional[str] = None
        # sync volume: how much data we actually write, per persisted key (aggregated across
        # kernels: which VARIABLE costs the most) and per kernel ("per user": which session
        # syncs the most). Only ACKed writes are recorded - rejected/errored flushes re-mark
        # their keys dirty and would double-count on retry. Value shape: [syncs, bytes].
        self.sync_count = 0
        self.sync_bytes_total = 0
        self.restore_bytes_total = 0
        self.sync_keys_dropped = 0
        self.sync_kernels_dropped = 0
        self._sync_by_key: Dict[str, List[int]] = {}
        self._sync_by_kernel: Dict[str, List[int]] = {}

    def incr(self, name: str, n: int = 1) -> None:
        """Increment a named integer counter by ``n`` (raises on an unknown counter)."""
        with self._lock:
            current = getattr(self, name)
            if not isinstance(current, int):
                raise AttributeError(f"{name!r} is not an integer counter")
            setattr(self, name, current + n)

    def record_backend_ok(self) -> None:
        """Mark a successful backend round trip (clears the last-error marker)."""
        with self._lock:
            self.backend_last_ok = time.monotonic()
            self.backend_last_error = None

    def record_backend_error(self, error: str) -> None:
        """Record the last backend error message (for the ``/resourcez`` block)."""
        with self._lock:
            self.backend_last_error = error

    def _bump_sync_table(self, table: Dict[str, List[int]], key: str, nbytes: int, dropped_counter: str) -> None:
        entry = table.get(key)
        if entry is None:
            if len(table) >= SYNC_TABLE_CAP:
                setattr(self, dropped_counter, getattr(self, dropped_counter) + 1)
                key = _OTHER
                entry = table.get(key)
            if entry is None:
                entry = table[key] = [0, 0]
        entry[0] += 1
        entry[1] += nbytes

    def record_sync(self, kernel_id: str, sizes: Dict[str, int]) -> None:
        """Record an ACKed flush batch: ``sizes`` maps persist key -> envelope byte length."""
        with self._lock:
            for key, nbytes in sizes.items():
                self.sync_count += 1
                self.sync_bytes_total += nbytes
                self._bump_sync_table(self._sync_by_key, key, nbytes, "sync_keys_dropped")
                self._bump_sync_table(self._sync_by_kernel, kernel_id, nbytes, "sync_kernels_dropped")

    def record_restore_bytes(self, nbytes: int) -> None:
        """Record the envelope bytes read by a successful restore."""
        with self._lock:
            self.restore_bytes_total += nbytes

    @staticmethod
    def _top_syncers(table: Dict[str, List[int]], label: str, limit: int, truncate: int = 0) -> List[Dict[str, Any]]:
        rows = sorted(table.items(), key=lambda kv: kv[1][1], reverse=True)[:limit]
        return [
            {
                label: (name[:truncate] if truncate and name != _OTHER else name),
                "syncs": syncs,
                "bytes": nbytes,
                "bytes_per_sync": nbytes // max(syncs, 1),
            }
            for name, (syncs, nbytes) in rows
        ]

    def as_dict(self, verbose: bool = False) -> Dict[str, Any]:
        """A snapshot for the ``/resourcez`` state block; adds a computed ok-age.

        ``verbose`` widens the per-key and per-kernel sync tables from the top 10 to the
        top 100 rows (by bytes) - pass ``/resourcez?verbose=1``. Kernel ids are truncated to
        an 8-char prefix: enough to grep the full id in the ``solara.state`` log lines,
        without exposing complete ids on an ops endpoint.
        """
        limit = 100 if verbose else 10
        with self._lock:
            last_ok = self.backend_last_ok
            age = None if last_ok is None else max(0.0, time.monotonic() - last_ok)
            return {
                "restore_attempts": self.restore_attempts,
                "restore_success": self.restore_success,
                "restore_bailout": self.restore_bailout,
                "restore_miss": self.restore_miss,
                "restore_schema_reset": self.restore_schema_reset,
                "flush_ok": self.flush_ok,
                "flush_rejected": self.flush_rejected,
                "flush_failures": self.flush_failures,
                "breaker_transitions": self.breaker_transitions,
                "superseded_closes": self.superseded_closes,
                "superseded_while_connected": self.superseded_while_connected,
                "backend_last_ok_age_seconds": age,
                "backend_last_error": self.backend_last_error,
                "sync_count": self.sync_count,
                "sync_bytes_total": self.sync_bytes_total,
                "sync_mb_total": round(self.sync_bytes_total / 1e6, 3),
                "restore_bytes_total": self.restore_bytes_total,
                "sync_keys_dropped": self.sync_keys_dropped,
                "sync_kernels_dropped": self.sync_kernels_dropped,
                "sync_by_key": self._top_syncers(self._sync_by_key, "key", limit),
                "sync_by_kernel": self._top_syncers(self._sync_by_kernel, "kernel", limit, truncate=8),
            }

    def _reset(self) -> None:
        """Zero every counter and marker (tests only)."""
        with self._lock:
            self.restore_attempts = 0
            self.restore_success = 0
            self.restore_bailout = 0
            self.restore_miss = 0
            self.restore_schema_reset = 0
            self.flush_ok = 0
            self.flush_rejected = 0
            self.flush_failures = 0
            self.breaker_transitions = 0
            self.superseded_closes = 0
            self.superseded_while_connected = 0
            self.backend_last_ok = None
            self.backend_last_error = None
            self.sync_count = 0
            self.sync_bytes_total = 0
            self.restore_bytes_total = 0
            self.sync_keys_dropped = 0
            self.sync_kernels_dropped = 0
            self._sync_by_key = {}
            self._sync_by_kernel = {}


_stats = Stats()


def stats() -> Stats:
    """Return the process-wide :class:`Stats` singleton."""
    return _stats


# --- structured log helpers (§7a line formats) --------------------------------------------
#
# The event name is the first token of the message; the logger is already named
# "solara.state", so the message carries no redundant prefix.

_RESTORE_LEVEL = {
    "success": logging.INFO,
    "miss": logging.DEBUG,
    "fresh-schema": logging.INFO,
    "timeout": logging.WARNING,
    "bailout": logging.ERROR,
}


def log_restore(result: str, *, kernel: str, key: Optional[str] = None, cause: Optional[str] = None) -> None:
    """Emit ``restore result=… kernel=… [key=…] [cause=…]`` (key/cause only when relevant)."""
    parts = [f"restore result={result}", f"kernel={kernel}"]
    if key is not None:
        parts.append(f"key={key}")
    if cause is not None:
        parts.append(f"cause={cause}")
    logger.log(_RESTORE_LEVEL.get(result, logging.INFO), " ".join(parts))


def log_flush(result: str, *, kernel: str, n_fields: int) -> None:
    """Emit ``flush result=ok|rejected|error kernel=… n_fields=…``."""
    level = logging.DEBUG if result == "ok" else logging.WARNING if result == "rejected" else logging.ERROR
    logger.log(level, "flush result=%s kernel=%s n_fields=%d", result, kernel, n_fields)


def log_breaker(transition: str, *, reason: str) -> None:
    """Emit ``breaker transition=open|half_open|closed reason=…`` (always WARNING, §5.3)."""
    logger.warning("breaker transition=%s reason=%s", transition, reason)


def log_close(reason: str, *, deleted: bool) -> None:
    """Emit ``close reason=… deleted=true|false``."""
    logger.info("close reason=%s deleted=%s", reason, "true" if deleted else "false")
