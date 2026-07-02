"""Per-process circuit breaker guarding the state backend (design §5.3).

A slow-not-down backend must not tax the interaction path: with the breaker open, both
restores (the takeover read on connect) and flushes skip the backend instantly instead of
each paying the connect deadline during a brownout. It is deliberately specified, not
gestured at:

- consecutive-failure threshold ``breaker_failures`` (default 3),
- open window ``breaker_window`` (default ``"30s"``) before a single half-open probe,
- half-open single-probe: exactly one trial is allowed once the window elapses; the
  probe's success closes the breaker, its failure re-opens it for another window.

Every transition logs one WARNING and bumps a counter (§7a). The clock is injectable so
tests drive the window deterministically without sleeping. The instance is thread-safe;
one process-wide instance (``solara.state.get_breaker()``) guards the backend, and both
restore and flush callers check :meth:`allow` before a backend call.
"""

import threading
import time
from typing import Callable, Optional

from solara.state._settings import state_settings
import solara.util

from .stats import log_breaker, stats

__all__ = ["CircuitBreaker"]

CLOSED = "closed"
OPEN = "open"
HALF_OPEN = "half_open"


class CircuitBreaker:
    def __init__(
        self,
        failures: Optional[int] = None,
        window: Optional[float] = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        """Create a breaker. ``failures``/``window`` default to the ``state`` settings when None."""
        self._failures_threshold = state_settings().breaker_failures if failures is None else failures
        if window is None:
            window = solara.util.parse_timedelta(state_settings().breaker_window)
        self._window = window
        self._clock = clock
        self._lock = threading.Lock()
        self._state = CLOSED
        self._consecutive_failures = 0
        self._opened_at = 0.0
        # in half_open: whether the single probe has already been handed out
        self._probe_used = False

    @property
    def state(self) -> str:
        """The stored breaker state: ``"closed"`` | ``"open"`` | ``"half_open"``."""
        with self._lock:
            return self._state

    def allow(self) -> bool:
        """Whether a backend call may proceed now.

        False while open (and before the window elapses). When the window elapses, the first
        call transitions to half_open and returns True once (the probe); further calls return
        False until :meth:`record_success` / :meth:`record_failure` resolves the probe.
        """
        with self._lock:
            if self._state == CLOSED:
                return True
            if self._state == OPEN:
                if self._clock() - self._opened_at >= self._window:
                    self._transition(HALF_OPEN, "window-elapsed")
                    self._probe_used = True
                    return True
                return False
            # half_open: exactly one probe outstanding
            if not self._probe_used:
                self._probe_used = True
                return True
            return False

    def record_success(self) -> None:
        """Record a backend success: closes the breaker (from half_open) or resets failures."""
        with self._lock:
            if self._state == CLOSED:
                self._consecutive_failures = 0
            else:
                self._transition(CLOSED, "probe-success" if self._state == HALF_OPEN else "success")

    def record_failure(self) -> None:
        """Record a backend failure: opens after N in a row, or re-opens a failed probe."""
        with self._lock:
            if self._state == HALF_OPEN:
                self._transition(OPEN, "probe-failure")
            elif self._state == CLOSED:
                self._consecutive_failures += 1
                if self._consecutive_failures >= self._failures_threshold:
                    self._transition(OPEN, f"consecutive-failures={self._consecutive_failures}")
            # a failure while OPEN keeps the current window (allow() gates it already)

    def _transition(self, new_state: str, reason: str) -> None:
        # caller holds self._lock
        if new_state == OPEN:
            self._opened_at = self._clock()
            self._probe_used = False
        elif new_state == CLOSED:
            self._consecutive_failures = 0
            self._probe_used = False
        self._state = new_state
        stats().incr("breaker_transitions")
        log_breaker(new_state, reason=reason)
