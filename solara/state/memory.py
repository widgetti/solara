"""In-process state backend: dict + lock, storing the same signed envelope bytes as Redis.

Fidelity is pinned on purpose (design §5.7): this backend stores the codec-encoded,
HMAC-signed envelope *bytes* (never live objects) and implements the same
takeover/flush/fence contract, so serialization bugs and fencing logic are exercised in
single-process dev and tests. It cannot cover network latency/timeout, torn-connection
behavior, or eviction — those need the two-process Redis test.
"""

import dataclasses
import hmac
import threading
import time
from typing import Callable, Dict, Optional

from .backend import StateBackend, TakeoverResult


@dataclasses.dataclass
class _Entry:
    generation: int
    session_hmac: bytes
    schema_tag: str
    fields: Dict[str, bytes]
    deadline: Optional[float]  # monotonic time after which the entry is expired; None = never


class MemoryStateBackend(StateBackend):
    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._store: Dict[str, _Entry] = {}
        self._lock = threading.Lock()
        # TTL is enforced lazily on access via this monotonic clock (no background thread);
        # tests override it to simulate expiry.
        self._clock = clock

    def _get_live(self, kernel_id: str) -> Optional[_Entry]:
        entry = self._store.get(kernel_id)
        if entry is None:
            return None
        if entry.deadline is not None and self._clock() >= entry.deadline:
            del self._store[kernel_id]
            return None
        return entry

    def takeover(self, kernel_id: str, session_hmac: bytes, schema_tag: str) -> TakeoverResult:
        with self._lock:
            entry = self._get_live(kernel_id)
            if entry is None:
                return TakeoverResult(reason="miss", generation=1, fields={})
            if not entry.session_hmac or not hmac.compare_digest(entry.session_hmac, session_hmac):
                return TakeoverResult(reason="identity-mismatch", generation=0, fields={})
            if entry.schema_tag != schema_tag:
                del self._store[kernel_id]
                return TakeoverResult(reason="schema-reset", generation=1, fields={})
            entry.generation += 1
            return TakeoverResult(reason="restored", generation=entry.generation, fields=dict(entry.fields))

    def flush(
        self,
        kernel_id: str,
        generation: int,
        fields: Dict[str, bytes],
        ttl: float,
        session_hmac: bytes,
        schema_tag: str,
    ) -> bool:
        if generation == 0:
            return False
        with self._lock:
            entry = self._get_live(kernel_id)
            deadline = None if ttl is None else self._clock() + ttl
            if entry is None:
                self._store[kernel_id] = _Entry(
                    generation=generation,
                    session_hmac=session_hmac,
                    schema_tag=schema_tag,
                    fields=dict(fields),
                    deadline=deadline,
                )
                return True
            if entry.generation != generation:
                return False
            entry.fields.update(fields)
            entry.session_hmac = session_hmac
            entry.schema_tag = schema_tag
            entry.deadline = deadline
            return True

    def peek_generation(self, kernel_id: str) -> Optional[int]:
        with self._lock:
            entry = self._get_live(kernel_id)
            return None if entry is None else entry.generation

    def delete(self, kernel_id: str, generation: Optional[int] = None) -> bool:
        with self._lock:
            entry = self._get_live(kernel_id)
            if entry is None:
                return False
            if generation is not None and entry.generation != generation:
                return False
            del self._store[kernel_id]
            return True
