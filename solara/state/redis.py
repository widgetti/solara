"""Redis state backend: one hash per kernel, fenced writes via atomic Lua scripts.

This is the v1 production backend for opt-in reactive state persistence (design §5.2/§5.5/
§5.7). It satisfies the exact same four-verb :class:`~solara.state.backend.StateBackend`
contract as the in-process memory backend, so serialization and fencing logic proven in dev
against the memory backend behave identically here. Every kernel is one Redis hash at
``{prefix}{kernel_id}`` with meta fields (``__generation__``, ``__session_id__``,
``__version__``) alongside the ``reactive:``-prefixed signed envelopes.

Atomicity is delegated to Redis, not to the design: ``takeover`` (verify -> bump -> read) and
``flush`` (fenced compare-then-write) are each a single Lua script registered once per client,
so an old instance's write is cleanly on one side of the generation bump. Values in and out are
opaque bytes (``decode_responses=False``); the envelopes are already codec-encoded + HMAC-signed
by the persistence manager. Redis/network errors propagate to callers (the worker/breaker/connect
paths already count and handle them); only the missing-``redis``-package import is wrapped.

Transparently covers Valkey/KeyDB/Dragonfly (Redis-protocol compatible via redis-py).
"""

import logging
from typing import Any, Dict, List, Optional, Sequence, Union

import solara.settings

from .backend import StateBackend, TakeoverResult

logger = logging.getLogger("solara.state.redis")

# --- Lua scripts (registered once per client; values passed via KEYS/ARGV only, never
# interpolated into the source). Redis Lua is 5.1; these avoid `unpack`/`table.unpack` and
# boolean returns so they run identically on real Redis and on fakeredis+lupa. -------------

# takeover: KEYS[1] = hash key; ARGV = [schema_tag, ttl_seconds, session_hmac_1, session_hmac_2, ...].
# Verify identity (verify-ANY across the candidate session HMACs, for key rotation) -> check schema
# -> bump generation -> refresh TTL -> read reactive:* fields, as one atomic unit. Returns a flat
# array: {reason, generation [, field, value]...}.
_LUA_TAKEOVER = """
if redis.call('EXISTS', KEYS[1]) == 0 then
    return {'miss', 1}
end
local stored_session = redis.call('HGET', KEYS[1], '__session_id__')
local identity_ok = false
if stored_session then
    for i = 3, #ARGV do
        if stored_session == ARGV[i] then
            identity_ok = true
            break
        end
    end
end
if not identity_ok then
    return {'identity-mismatch', 0}
end
local stored_version = redis.call('HGET', KEYS[1], '__version__')
if (not stored_version) or (stored_version ~= ARGV[1]) then
    redis.call('DEL', KEYS[1])
    return {'schema-reset', 1}
end
local generation = redis.call('HINCRBY', KEYS[1], '__generation__', 1)
local ttl = tonumber(ARGV[2])
if ttl and ttl >= 1 then
    redis.call('EXPIRE', KEYS[1], ttl)
end
local all = redis.call('HGETALL', KEYS[1])
local out = {'restored', generation}
for i = 1, #all, 2 do
    local field = all[i]
    -- return every data field, i.e. everything except the reserved __*__ meta fields
    -- (mirrors the memory backend, which stores meta separately from its fields dict)
    if string.sub(field, 1, 2) ~= '__' then
        table.insert(out, field)
        table.insert(out, all[i + 1])
    end
end
return out
"""

# flush: KEYS[1] = hash key; ARGV = [generation, ttl_seconds, session_hmac, schema_tag,
# field1, value1, field2, value2, ...]. The ONLY write path (design §5.5): compare-then-write
# under the generation fence, all inside the script; writes NOTHING when fenced out.
# Returns 1 on write, 0 on rejection.
_LUA_FLUSH = """
local claimed = tonumber(ARGV[1])
if claimed == 0 then
    return 0
end
if redis.call('EXISTS', KEYS[1]) == 1 then
    local stored = tonumber(redis.call('HGET', KEYS[1], '__generation__'))
    if (not stored) or (stored ~= claimed) then
        return 0
    end
elseif claimed ~= 1 then
    -- create-on-missing is only legitimate from the fresh-start generation (1). A higher claimed
    -- generation on a MISSING key means the hash was deleted / evicted / TTL-expired out from under
    -- a still-live older instance; recreating it here would RESURRECT stale data at a stale
    -- generation and fence out the legitimate new owner. Refuse -> the caller's rejection protocol
    -- re-takes over (now a miss -> generation 1) and re-establishes cleanly.
    return 0
end
redis.call('HSET', KEYS[1], '__generation__', ARGV[1])
redis.call('HSET', KEYS[1], '__session_id__', ARGV[3])
redis.call('HSET', KEYS[1], '__version__', ARGV[4])
for i = 5, #ARGV, 2 do
    redis.call('HSET', KEYS[1], ARGV[i], ARGV[i + 1])
end
local ttl = tonumber(ARGV[2])
if ttl and ttl >= 1 then
    redis.call('EXPIRE', KEYS[1], ttl)
end
return 1
"""

# delete (fenced): KEYS[1] = hash key; ARGV = [generation]. Delete iff the stored generation
# still matches. Returns 1 if deleted, 0 otherwise. (The unfenced delete is a plain DEL.)
_LUA_DELETE = """
if redis.call('EXISTS', KEYS[1]) == 0 then
    return 0
end
local stored = tonumber(redis.call('HGET', KEYS[1], '__generation__'))
if (not stored) or (stored ~= tonumber(ARGV[1])) then
    return 0
end
redis.call('DEL', KEYS[1])
return 1
"""


class RedisStateBackend(StateBackend):
    """Redis-backed state backend (design §5.2/§5.5/§5.7).

    Constructed with no arguments by ``get_backend()``: it reads ``solara.settings.state.url``
    (the redis DSN) and ``prefix``, and builds a sync ``redis.Redis`` client whose socket
    timeouts bound *every* operation (the connect deadline in commit 2 relies on this). The
    ``client`` kwarg and the :meth:`_make_client` factory are the test-injection seam.
    """

    # a genuinely shared, cross-process store: the server may shorten the orphan cull (§5.4).
    shared = True

    def __init__(self, client: Optional[Any] = None) -> None:
        self._prefix = solara.settings.state.prefix
        # the client is the injection seam: tests pass a fakeredis client (optionally sharing one
        # FakeServer across two backend instances to model the two-instances-one-redis topology);
        # in production _make_client() builds a real client from settings.
        self.client = client if client is not None else self._make_client()
        # register the atomic scripts once; each Script is bound to this client (EVALSHA + fallback)
        self._takeover_script = self.client.register_script(_LUA_TAKEOVER)
        self._flush_script = self.client.register_script(_LUA_FLUSH)
        self._delete_script = self.client.register_script(_LUA_DELETE)
        self._check_maxmemory_policy()

    def _check_maxmemory_policy(self) -> None:
        # design §7: surface a dangerous eviction policy at connect time. `noeviction` refuses
        # writes rather than dropping live sessions; an lru/lfu policy silently evicts persisted
        # state under memory pressure (the "invisible worst case"). Best-effort: a CONFIG-disabled
        # or managed Redis that hides CONFIG must never block startup.
        try:
            raw = self.client.config_get("maxmemory-policy")  # type: ignore[attr-defined]
            policy = raw.get("maxmemory-policy") if isinstance(raw, dict) else raw
            if isinstance(policy, bytes):
                policy = policy.decode("utf-8", "replace")
            if not policy:
                return
            if "lru" in policy or "lfu" in policy or "random" in policy:
                logger.warning(
                    "Redis maxmemory-policy is %r: under memory pressure this EVICTS live persisted "
                    "state (silent session loss). Use 'noeviction' and alert on memory. See "
                    "solara.dev state-persistence deploying docs.",
                    policy,
                )
            else:
                logger.info("Redis maxmemory-policy is %r (state persistence).", policy)
        except Exception as exc:  # noqa - never let an observability check break startup
            logger.debug("could not read Redis maxmemory-policy: %s", exc)

    def _make_client(self) -> Any:
        # LAZY import: redis is an optional dependency, required only when this backend is selected.
        try:
            import redis
        except ImportError as exc:  # pragma: no cover - exercised via monkeypatched sys.modules
            raise ImportError(
                "the redis state backend requires the 'redis' package. Install it with `pip install solara[redis]` (or `pip install redis`)."
            ) from exc
        st = solara.settings.state
        if not st.url:
            raise ValueError("SOLARA_STATE_URL must be set to a redis DSN (e.g. redis://localhost:6379/0) for the redis state backend")
        # socket_timeout bounds every op incl. peek_generation; socket_connect_timeout bounds connect.
        # decode_responses stays False: envelopes are raw bytes and must round-trip byte-for-byte.
        return redis.Redis.from_url(
            st.url,
            socket_timeout=st.connect_timeout,
            socket_connect_timeout=st.connect_timeout,
            decode_responses=False,
        )

    def _key(self, kernel_id: str) -> str:
        return self._prefix + kernel_id

    def _takeover_ttl_seconds(self) -> int:
        # takeover has no ttl argument, but the design refreshes the TTL on connect (§5.2); use the
        # same kernel-scoped TTL the flush path uses so connect and write agree.
        from .persist import _default_ttl

        return _ttl_to_seconds(_default_ttl())

    def takeover(self, kernel_id: str, session_hmacs: "Union[bytes, Sequence[bytes]]", schema_tag: str) -> TakeoverResult:
        # bytes IS a Sequence[int]: a bare-bytes arg would spread to ints and silently never match.
        if isinstance(session_hmacs, (bytes, bytearray)):
            session_hmacs = (bytes(session_hmacs),)
        # ARGV = [schema_tag, ttl, *candidate session hmacs] (verify-ANY for key rotation)
        args = [schema_tag, self._takeover_ttl_seconds(), *session_hmacs]
        raw = self._takeover_script(keys=[self._key(kernel_id)], args=args)
        reason = _as_text(raw[0])
        generation = int(raw[1])
        fields: Dict[str, bytes] = {}
        rest = raw[2:]
        for i in range(0, len(rest), 2):
            fields[_as_text(rest[i])] = _as_bytes(rest[i + 1])
        return TakeoverResult(reason=reason, generation=generation, fields=fields)

    def flush(
        self,
        kernel_id: str,
        generation: int,
        fields: Dict[str, bytes],
        ttl: float,
        session_hmac: bytes,
        schema_tag: str,
    ) -> bool:
        args: List[Any] = [generation, _ttl_to_seconds(ttl), session_hmac, schema_tag]
        for field_name, value in fields.items():
            args.append(field_name)
            args.append(value)
        return bool(self._flush_script(keys=[self._key(kernel_id)], args=args))

    def peek_generation(self, kernel_id: str) -> Optional[int]:
        raw = self.client.hget(self._key(kernel_id), "__generation__")
        return None if raw is None else int(raw)

    def delete(self, kernel_id: str, generation: Optional[int] = None) -> bool:
        if generation is None:
            return bool(self.client.delete(self._key(kernel_id)))
        return bool(self._delete_script(keys=[self._key(kernel_id)], args=[generation]))


def _ttl_to_seconds(ttl: Optional[float]) -> int:
    # EXPIRE takes an integer seconds >= 1. Only an explicitly absent/disabled ttl (None or <= 0)
    # means "no expiry" (-1 sentinel, which the scripts skip). A *positive* sub-second ttl must
    # NOT silently become no-expiry (a misconfigured SOLARA_STATE_TTL="0.5s" would otherwise leave
    # keys in Redis forever) - floor it to 1s. Kernel TTLs are hours in practice.
    if ttl is None or ttl <= 0:
        return -1
    return max(1, int(ttl))


def _as_text(value: Any) -> str:
    return value.decode("utf-8") if isinstance(value, (bytes, bytearray)) else str(value)


def _as_bytes(value: Any) -> bytes:
    if isinstance(value, bytes):
        return value
    if isinstance(value, bytearray):
        return bytes(value)
    return str(value).encode("utf-8")
