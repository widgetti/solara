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
from typing import Callable, Dict, Optional, Sequence, Union

from .backend import StateBackend, TakeoverResult


@dataclasses.dataclass
class _Entry:
    generation: int
    session_hmac: bytes
    schema_tag: str
    fields: Dict[str, bytes]
    deadline: Optional[float]  # monotonic time after which the entry is expired; None = never


class MemoryStateBackend(StateBackend):
    # in-process only: state dies with the process, so the shortened orphan cull (§5.4) must
    # not apply (it would only lose state, never save a failover).
    shared = False

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

    def _claim(self, kernel_id: str, session_hmacs: Sequence[bytes], schema_tag: str) -> None:
        """Write the fresh-start entry (generation 1, no fields) for claim-on-miss.

        Caller holds ``self._lock``. Stores the FIRST candidate hmac as the identity (there is no
        stored identity to verify against on a miss; the first candidate is the current signing
        key by the sign-first rotation convention). No candidates -> no claim (fail open to the
        pre-claim behavior rather than storing an unverifiable empty identity).
        """
        first = bytes(session_hmacs[0]) if session_hmacs else b""
        if not first:
            return
        from .persist import _default_ttl

        self._store[kernel_id] = _Entry(
            generation=1,
            session_hmac=first,
            schema_tag=schema_tag,
            fields={},
            deadline=self._clock() + _default_ttl(),
        )

    def takeover(self, kernel_id: str, session_hmacs: "Union[bytes, Sequence[bytes]]", schema_tag: str) -> TakeoverResult:
        # bytes IS a Sequence[int]: a bare-bytes arg would iterate to ints and silently never match.
        if isinstance(session_hmacs, (bytes, bytearray)):
            session_hmacs = (bytes(session_hmacs),)
        with self._lock:
            entry = self._get_live(kernel_id)
            if entry is None:
                # claim-on-miss (fencing for never-flushed kernels): write the fresh-start
                # generation NOW instead of waiting for the first flush. Without the claim,
                # peek_generation() stays None until something is flushed, so a kernel that never
                # persists a value (e.g. a login form pre-login) is an UNFENCEABLE zombie: after a
                # cross-node takeover, _reuse_context_is_stale can never supersede the old context
                # and it keeps re-serving stale widgets. The claim stores the claimer's identity
                # (first candidate = the current signing key, sign-first convention) and the same
                # TTL as a takeover refresh, so an abandoned claim simply expires.
                self._claim(kernel_id, session_hmacs, schema_tag)
                return TakeoverResult(reason="miss", generation=1, fields={})
            # verify-ANY (key rotation): the stored identity may have been written under a now-old
            # key; constant-time compare against every candidate.
            if not entry.session_hmac or not any(hmac.compare_digest(entry.session_hmac, candidate) for candidate in session_hmacs):
                return TakeoverResult(reason="identity-mismatch", generation=0, fields={})
            if entry.schema_tag != schema_tag:
                del self._store[kernel_id]
                # same unfenceable-zombie hole as the miss branch: the caller proceeds at
                # generation 1 with fresh state, so claim the key for it under the new schema tag.
                self._claim(kernel_id, session_hmacs, schema_tag)
                return TakeoverResult(reason="schema-reset", generation=1, fields={})
            entry.generation += 1
            # refresh the deadline on connect, matching the redis Lua's EXPIRE on takeover
            # (design §5.2: TTL refreshed on write AND on connect); derive the ttl the same
            # way the redis backend does so the two stay in lockstep
            from .persist import _default_ttl

            entry.deadline = self._clock() + _default_ttl()
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
                # create-on-missing only from the fresh-start generation (1); a higher claimed gen
                # on a missing key means it was deleted/evicted under a stale instance - recreating
                # would resurrect stale data at a stale generation. Refuse (see redis _LUA_FLUSH).
                if generation != 1:
                    return False
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
