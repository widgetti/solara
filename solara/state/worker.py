"""Per-kernel debounced write-behind flush worker (design §5.3 + §5.5).

State changes do not align with websocket message boundaries - tasks, threads, timers and
asyncio callbacks all write reactives long after (or with no) triggering message. So every
mutation source is treated uniformly: the ``subscribe_change`` dirty-mark (persist.py)
arms this worker, which coalesces rapid marks into one flush ~``flush_debounce`` later,
snapshots + serializes off the hot path (inside :meth:`KernelStatePersistence.flush_now`),
and writes through the fenced backend guarded by the circuit breaker.

Threading model: **one background daemon thread per kernel** - the simplest correct thing
(a kernel already owns per-kernel objects; a shared timer thread would need a heap of
deadlines and careful cancellation for no real gain at solara's kernel counts). The thread
sleeps on a ``Condition`` until a deadline, so it costs nothing while idle.

The worker never raises out of its thread: every failure path logs and counts. It routes
:class:`FlushOutcome` per the design - a backend ERROR feeds the breaker, a fenced REJECT
feeds the bounded rejection protocol (§5.5), a serialize failure already disabled
persistence (§4.3). A breaker-open window never strands dirty keys: the worker re-arms the
timer while keys remain, so the first flush after the breaker closes drains them.
"""

import logging
import threading
import time
from typing import Callable, Optional

import solara.settings
import solara.util

from .breaker import CircuitBreaker
from .persist import FlushOutcome, KernelStatePersistence
from .stats import stats

logger = logging.getLogger("solara.state")

__all__ = ["KernelFlushWorker", "FlushOutcome"]


def _parse_debounce(text: str) -> float:
    """Parse ``flush_debounce`` (e.g. ``"300ms"``, ``"1s"``) to seconds.

    ``solara.util.parse_timedelta`` supports d/h/m/s and bare seconds but NOT milliseconds
    (``"300ms"`` would misparse via its ``s`` branch), so ``ms`` is handled here first; a
    bare number is accepted as float seconds.
    """
    text = str(text).strip()
    if text.endswith("ms"):
        return float(text[:-2]) / 1000.0
    return solara.util.parse_timedelta(text)


def _default_debounce() -> float:
    return _parse_debounce(solara.settings.state.flush_debounce)


class KernelFlushWorker:
    """The per-kernel debounced write-behind worker.

    :param manager: the kernel's :class:`KernelStatePersistence`.
    :param breaker: the process-wide :class:`CircuitBreaker` guarding the backend.
    :param has_connected_page: returns whether this kernel currently has a CONNECTED page
        (the server wires it to ``context.page_status``); drives the rejection protocol.
    :param on_superseded: called when this kernel is legitimately superseded (orphan): the
        server wires it to close the context with ``close_reason="superseded"``.
    :param debounce: coalescing window in seconds; ``None`` reads ``state.flush_debounce``.
    """

    def __init__(
        self,
        manager: KernelStatePersistence,
        *,
        breaker: CircuitBreaker,
        has_connected_page: Callable[[], bool],
        on_superseded: Callable[[], None],
        debounce: Optional[float] = None,
    ) -> None:
        self.manager = manager
        self.breaker = breaker
        self._has_connected_page = has_connected_page
        self._on_superseded = on_superseded
        self._debounce = _default_debounce() if debounce is None else debounce

        self._cond = threading.Condition()
        self._deadline: Optional[float] = None
        self._stop = False
        self._closed = False
        self._thread: Optional[threading.Thread] = None

        # rejection-protocol budget (§5.5): at most one re-takeover per connection epoch
        self._epoch_lock = threading.Lock()
        self._retakeovers_this_epoch = 0

        # test/observability hooks: every completed attempt (incl. a breaker-open skip) bumps
        # flush_attempts and sets flush_completed, so tests synchronize without long sleeps.
        self._flush_cond = threading.Condition()
        self.flush_attempts = 0
        self.flush_completed = threading.Event()

    # --- lifecycle ------------------------------------------------------------------------

    def start(self) -> None:
        """Wire the manager's flush scheduler and start the background thread."""
        self.manager.set_flush_scheduler(self.schedule)
        self._thread = threading.Thread(
            target=self._run,
            name=f"solara-state-flush-{self.manager.kernel_id}",
            daemon=True,
        )
        self._thread.start()
        # a write may have landed between attach and start; do not strand it
        if self.manager.dirty_keys:
            self.schedule()

    def schedule(self) -> None:
        """Arm a debounced flush (leading-edge: coalesces marks within the window into one)."""
        with self._cond:
            if self._deadline is None and not self._stop:
                self._deadline = time.monotonic() + self._debounce
                self._cond.notify_all()

    def new_epoch(self) -> None:
        """Reset the re-takeover budget; the server calls this on each websocket connect (§5.5)."""
        with self._epoch_lock:
            self._retakeovers_this_epoch = 0

    @property
    def retakeovers_this_epoch(self) -> int:
        with self._epoch_lock:
            return self._retakeovers_this_epoch

    def stop(self) -> None:
        """Signal the background thread to exit (does not flush; does not join)."""
        with self._cond:
            self._stop = True
            self._cond.notify_all()

    def close(self, timeout: float = 5.0) -> None:
        """Stop the worker and do a bounded, best-effort final flush, then detach the manager.

        CONTRACT: **call this OUTSIDE ``context.lock``.** :meth:`flush_now` snapshots under the
        reactive lock (never ``context.lock``) and writes to the backend outside every lock,
        so holding ``context.lock`` here would risk the documented I/O-under-lock deadlock
        (docs/reactive-initialization-lock-deadlock.md). The server wires this single call as
        the context's ``on_close`` for a persistence-enabled kernel.
        """
        if self._closed:
            return
        self._closed = True
        self.stop()
        thread = self._thread
        # never self-join: the orphan path runs on this very thread (on_superseded -> context
        # close -> on_close -> close())
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=timeout)
        self.manager.set_flush_scheduler(None)

        manager = self.manager
        try:
            if not manager.disabled and manager.dirty_keys and self.breaker.allow():
                outcome = manager.flush_now()
                if outcome == FlushOutcome.OK or outcome == FlushOutcome.REJECTED:
                    # a reject at teardown means we were superseded: flush-and-leave (§5.4),
                    # no reclaim here. Either way the backend round-tripped: success for health.
                    self.breaker.record_success()
                elif outcome == FlushOutcome.ERROR:
                    self.breaker.record_failure()
                else:
                    # NOTHING / DISABLED: resolve any consumed half-open probe (see _route) so a
                    # final flush at teardown cannot leave the process-wide breaker wedged.
                    self.breaker.resolve_probe()
        except Exception:  # noqa
            logger.exception("final state flush failed for kernel %s", manager.kernel_id)
        # unsubscribe + detach (its internal flush is a no-op once we've drained above)
        try:
            manager.close()
        except Exception:  # noqa
            logger.exception("manager close failed for kernel %s", manager.kernel_id)

    # --- background loop ------------------------------------------------------------------

    def _run(self) -> None:
        while not self._stop:
            with self._cond:
                while not self._stop and self._deadline is None:
                    self._cond.wait()
                if self._stop:
                    return
                while not self._stop and self._deadline is not None:
                    remaining = self._deadline - time.monotonic()
                    if remaining <= 0:
                        break
                    self._cond.wait(timeout=remaining)
                if self._stop:
                    return
                if self._deadline is None:
                    continue
                self._deadline = None
            self._attempt_flush()

    def _attempt_flush(self) -> None:
        try:
            self._flush_once()
        except Exception:  # noqa - the worker must never raise out of its thread
            logger.exception("state flush worker error for kernel %s", self.manager.kernel_id)
        finally:
            self.flush_completed.set()
            with self._flush_cond:
                self.flush_attempts += 1
                self._flush_cond.notify_all()

    def _rearm(self) -> None:
        # retry later: re-arm the debounce timer so a breaker-open (or errored) flush is not
        # stranded - dirty keys drain on the next attempt once the backend recovers.
        with self._cond:
            if not self._stop:
                self._deadline = time.monotonic() + self._debounce
                self._cond.notify_all()

    def _flush_once(self) -> None:
        manager = self.manager
        if manager.disabled or self._stop:
            return
        if not manager.dirty_keys:
            return
        if not self.breaker.allow():
            # breaker open: leave keys dirty, retry when the window may let a probe through
            self._rearm()
            return
        self._route(manager.flush_now())

    def _route(self, outcome: FlushOutcome) -> None:
        if outcome == FlushOutcome.OK:
            self.breaker.record_success()
        elif outcome == FlushOutcome.ERROR:
            self.breaker.record_failure()
            self._rearm()
        elif outcome == FlushOutcome.REJECTED:
            # a fence rejection means the backend is healthy but another instance owns the
            # generation: NOT a breaker failure, but the rejection protocol.
            self.breaker.record_success()
            self._handle_rejection()
        else:
            # NOTHING (no dirty keys) / DISABLED (serialize failure; hash deleted): not a backend
            # health signal, but allow() above may have consumed a half-open probe - resolve it so
            # the breaker cannot wedge HALF_OPEN (a genuinely down backend re-opens on next flush).
            self.breaker.resolve_probe()

    # --- rejection protocol (§5.5, bounded) -----------------------------------------------

    def _handle_rejection(self) -> None:
        manager = self.manager
        if not self._has_connected_page():
            # orphan, legitimately superseded: stop persisting, let the server close with
            # reason=superseded (flush-and-leave, §5.4). No reclaim.
            stats().incr("superseded_closes")
            logger.warning("kernel %s superseded (no connected page); stopping flush worker", manager.kernel_id)
            self._stop = True
            try:
                self._on_superseded()
            except Exception:  # noqa
                logger.exception("on_superseded callback failed for kernel %s", manager.kernel_id)
            return

        if self.retakeovers_this_epoch >= 1:
            # already re-took this epoch and got rejected again -> concede: keep serving the
            # live session from memory, stop persisting, log loudly (broken LB stickiness /
            # cross-instance multi-tab / attack signature, §5.5).
            manager.disabled = True
            stats().incr("superseded_while_connected")
            logger.warning(
                "superseded-while-connected kernel=%s: conceding, serving from memory (check LB stickiness)",
                manager.kernel_id,
            )
            self._stop = True
            return

        # connected page, first rejection this epoch: re-takeover ONCE.
        if not self.breaker.allow():
            self._rearm()  # cannot re-takeover with the breaker open; retry later
            return
        try:
            # re-takeover is same-process: the stored identity was written by THIS manager's
            # primary session_hmac, so a single-candidate verify-any is correct here.
            result = manager.backend.takeover(manager.kernel_id, [manager.session_hmac], manager.schema_tag)
        except Exception:  # noqa
            self.breaker.record_failure()
            stats().incr("flush_failures")
            stats().record_backend_error("re-takeover raised")
            logger.exception("re-takeover raised for kernel %s", manager.kernel_id)
            self._rearm()
            return
        self.breaker.record_success()
        with self._epoch_lock:
            self._retakeovers_this_epoch += 1
        # DISCARD result.fields: in-memory state is authoritative here (do not apply the read).
        manager.generation = result.generation
        manager.mark_all_dirty()
        outcome = manager.flush_now()
        if outcome == FlushOutcome.REJECTED:
            self._handle_rejection()  # budget now spent -> concede
        elif outcome == FlushOutcome.ERROR:
            self.breaker.record_failure()
            self._rearm()
        elif outcome == FlushOutcome.OK:
            self.breaker.record_success()

    # --- test synchronization -------------------------------------------------------------

    def wait_for_flushes(self, n: int, timeout: float = 2.0) -> bool:
        """Block until at least ``n`` flush attempts have completed. Returns False on timeout."""
        deadline = time.monotonic() + timeout
        with self._flush_cond:
            while self.flush_attempts < n:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return False
                self._flush_cond.wait(remaining)
            return True
