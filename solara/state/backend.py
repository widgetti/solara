"""The four-verb state backend contract.

The interface is deliberately not Redis-shaped: a MutableMapping cannot express fenced
writes, so the contract is exactly the four verbs the persistence feature needs, with the
atomicity requirements stated here rather than delegated to a particular store's features.
The Redis backend (Lua hash-per-kernel) and the in-process memory backend both satisfy
this identical contract, so serialization and fencing logic are exercised in dev too.
"""

import abc
import dataclasses
from typing import Dict, Optional


@dataclasses.dataclass
class TakeoverResult:
    """Outcome of a takeover attempt.

    - `reason`: one of "restored" | "miss" | "identity-mismatch" | "schema-reset".
    - `generation`: the generation this instance now owns for subsequent fenced flushes.
      A value of 0 means "no write rights" (identity mismatch) and callers must not flush.
    - `fields`: envelope bytes per persisted field; empty unless `reason == "restored"`.
    """

    reason: str
    generation: int
    fields: Dict[str, bytes]


class StateBackend(abc.ABC):
    """Abstract base for state backends (ABC, not a Protocol, so shared logic can live here)."""

    # whether this backend is genuinely shared across processes/instances (Redis: True). The
    # server gates the shortened orphan cull on this (§5.4): shortening only makes sense when
    # state outlives the kernel in a shared store. Defaults True; single-process backends
    # override to False.
    shared: bool = True

    @abc.abstractmethod
    def takeover(self, kernel_id: str, session_hmac: bytes, schema_tag: str) -> TakeoverResult:
        """Atomically verify identity, bump the generation, and read all envelopes.

        Verify-then-bump-then-read as one atomic unit. Semantics:

        - Key missing: write NOTHING; return reason="miss", generation=1, fields={}.
          (The hash is created only by the first legitimate flush, which writes identity.)
        - Key exists but stored session-HMAC is absent or != `session_hmac`: write nothing;
          return reason="identity-mismatch", generation=0 (no write rights granted).
        - Key exists, identity matches, but stored schema tag != `schema_tag`: DELETE the
          hash; return reason="schema-reset", generation=1 (clean redeploy reset).
        - Key exists, identity and schema match: bump the stored generation and return
          reason="restored" with the new generation and all persisted fields.

        Must never write on a miss (an unauthenticated client must not be able to create
        keys or bump other users' generations).
        """

    @abc.abstractmethod
    def flush(
        self,
        kernel_id: str,
        generation: int,
        fields: Dict[str, bytes],
        ttl: float,
        session_hmac: bytes,
        schema_tag: str,
    ) -> bool:
        """Atomically write `fields` iff `generation` still matches (fenced). The only write path.

        - `generation == 0`: always returns False (no write rights), writes nothing.
        - Key missing: create it with the claimed `generation`, the identity fields
          (`session_hmac`, `schema_tag`), the given `fields`, and `ttl`; return True.
        - Key exists and stored generation == `generation`: merge `fields`, refresh identity
          and `ttl`; return True.
        - Key exists and stored generation != `generation`: return False, write nothing.
        """

    @abc.abstractmethod
    def peek_generation(self, kernel_id: str) -> Optional[int]:
        """Return the stored generation, or None if the key is absent/expired (cheap, no bump)."""

    @abc.abstractmethod
    def delete(self, kernel_id: str, generation: Optional[int] = None) -> bool:
        """Delete the key. If `generation` is given, delete only when the stored generation matches (fenced).

        Returns True if a key was deleted, False otherwise.
        """
