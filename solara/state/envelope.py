"""Signed, self-describing envelopes for persisted reactive state.

Every persisted value is codec-encoded and wrapped in an HMAC-SHA-256 signed
envelope that is verified *before* any payload is decoded, so "Redis write access"
never becomes "arbitrary code execution" on its own. The signature binds the
`kernel_id` and `field_name` (context binding), so an envelope cannot be replayed
into a different kernel or a different reactive variable. The generation/fencing
token is deliberately NOT part of the signature (a takeover bumps the generation
before the restore read, so a generation-bound envelope could never verify).
"""

import base64
import dataclasses
import datetime
import decimal
import enum
import hashlib
import hmac
import json
import pickle
import sys
import uuid
from typing import Any, Callable, Dict, List, Optional, Tuple

import solara.settings

__all__ = [
    "encode",
    "decode",
    "register_codec",
    "session_hmac",
    "EnvelopeError",
    "HmacError",
    "CodecError",
    "SerializeError",
]

# binary layout (all lengths are 4-byte big-endian):
#   version(1) | len(key_id) key_id | len(codec) codec | len(payload) payload | hmac(32)
_FORMAT_VERSION = 1
_HMAC_SIZE = 32
_KEY_ID_SIZE = 8  # short hash of the secret key; position-independent so rotation works


class EnvelopeError(Exception):
    """Base class for all envelope errors."""


class HmacError(EnvelopeError):
    """Signature verification failed: tampered, wrong key, or cross-kernel/field replay."""


class CodecError(EnvelopeError):
    """The codec is unknown, disabled, or failed to decode a payload."""


class SerializeError(EnvelopeError):
    """A value cannot be serialized by the selected codec (raised at encode time)."""


# --- codec registry -------------------------------------------------------

Dumps = Callable[[Any], bytes]
Loads = Callable[[bytes], Any]
_CODECS: Dict[str, Tuple[Dumps, Loads]] = {}


def register_codec(name: str, dumps: Dumps, loads: Loads) -> None:
    """Register a codec: `dumps` maps a value to bytes, `loads` maps bytes back to a value."""
    _CODECS[name] = (dumps, loads)


def _get_codec(name: str) -> Tuple[Dumps, Loads]:
    try:
        return _CODECS[name]
    except KeyError:
        raise CodecError(f"unknown codec {name!r}; registered codecs: {sorted(_CODECS)}")


# --- json codec with faithful type coercion -------------------------------

# reserved dict marker for type-tagged values; recursive
_MARKER = "__solara_type__"


def _get_numpy():
    # numpy is an optional dependency: only used to coerce its scalar types
    try:
        import numpy
    except ImportError:
        return None
    return numpy


def _coerce_numpy(value: Any) -> Any:
    # np.integer -> int, np.floating -> float. Lossy-to-python is fine and intended:
    # numpy scalars round-trip through JSON as plain python numbers.
    numpy = _get_numpy()
    if numpy is not None:
        if isinstance(value, numpy.integer):
            return int(value)
        if isinstance(value, numpy.floating):
            return float(value)
    return _UNSET


_UNSET = object()


def _get_pydantic_base_model() -> Optional[type]:
    # pydantic stays an optional dependency: a value can only BE a BaseModel instance if
    # pydantic is already imported, so sys.modules is sufficient on the encode side
    pydantic = sys.modules.get("pydantic")
    return None if pydantic is None else pydantic.BaseModel


def _class_tag(value: Any) -> str:
    cls = type(value)
    return f"{cls.__module__}:{cls.__qualname__}"


def _to_jsonable(value: Any) -> Any:
    # enum first: IntEnum/StrEnum members are also int/str instances
    if isinstance(value, enum.Enum):
        cls = type(value)
        return {_MARKER: "enum", "type": f"{cls.__module__}:{cls.__qualname__}", "value": _to_jsonable(value.value)}
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, dict):
        # strictness guards against silent corruption: a reserved-marker key would be
        # misread as a tagged value at decode, and json stringifies non-str keys ({1: ..}
        # would come back as {"1": ..}) - fail loud at the first write instead
        if _MARKER in value:
            raise SerializeError(f"dict key {_MARKER!r} is reserved by the json codec")
        for key in value:
            if not isinstance(key, str):
                raise SerializeError(f"dict keys must be str for the json codec (found {type(key).__name__} key {key!r}); json would silently stringify it")
        return {key: _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, tuple):
        # tuple -> list round-trip caveat (JSON has no tuple type)
        return [_to_jsonable(item) for item in value]
    if isinstance(value, (set, frozenset)):
        tag = "frozenset" if isinstance(value, frozenset) else "set"
        return {_MARKER: tag, "value": [_to_jsonable(item) for item in value]}
    # datetime before date: datetime is a subclass of date
    if isinstance(value, datetime.datetime):
        return {_MARKER: "datetime", "value": value.isoformat()}
    if isinstance(value, datetime.date):
        return {_MARKER: "date", "value": value.isoformat()}
    if isinstance(value, datetime.time):
        return {_MARKER: "time", "value": value.isoformat()}
    if isinstance(value, uuid.UUID):
        return {_MARKER: "uuid", "value": str(value)}
    if isinstance(value, decimal.Decimal):
        return {_MARKER: "decimal", "value": str(value)}
    if isinstance(value, (bytes, bytearray)):
        return {_MARKER: "bytes", "value": base64.b64encode(bytes(value)).decode("ascii")}
    # self-describing structured types: the class travels WITH the value (module:qualname),
    # so deserialization needs no target class declared anywhere - which is what makes
    # `solara.reactive(None, persist=True)` work when a model lands in it later. Decode
    # verifies the resolved class is a BaseModel/dataclass before instantiating (never an
    # arbitrary class), and runs only after HMAC verification. Trade-off, documented:
    # renaming/moving the class makes old envelopes undecodable (-> bail-out; bump
    # SOLARA_STATE_SCHEMA_TAG for a clean reset instead).
    base_model = _get_pydantic_base_model()
    if base_model is not None and isinstance(value, base_model):
        # model_dump() (python mode) keeps nested exotic types (datetime, Enum, nested
        # models become dicts pydantic re-validates) for our recursive tagging; v1: dict()
        dump = value.model_dump() if hasattr(value, "model_dump") else value.dict()  # type: ignore[attr-defined]
        return {_MARKER: "pydantic", "type": _class_tag(value), "value": _to_jsonable(dump)}
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        # recursive tagging is self-describing at every level, so reconstruction is
        # cls(**fields) with already-decoded children - no type-hint introspection.
        # init=False fields are derived state: recomputed by __post_init__/defaults, not stored
        fields = {f.name: _to_jsonable(getattr(value, f.name)) for f in dataclasses.fields(value) if f.init}
        return {_MARKER: "dataclass", "type": _class_tag(value), "value": fields}
    coerced = _coerce_numpy(value)
    if coerced is not _UNSET:
        return coerced
    tp = type(value)
    raise SerializeError(f"cannot serialize object of type {tp.__module__}.{tp.__qualname__} with the json codec")


def _resolve(dotted: str) -> Any:
    # Resolve a "module:qualname" tag to the object it names. The tag comes from an envelope
    # that HMAC verification has already accepted - but a *forged* tag can be HMAC-valid too, if
    # the attacker holds the secret (a leaked secret is medium severity: forge/tamper state). We
    # deliberately do NOT let that escalate to RCE: the default JSON codec must stay code-exec
    # free even when the secret leaks (pickle is the separate, deployer-gated path for code exec).
    # Three rules enforce that here, and each caller ALSO gates the resolved class to its own kind
    # (enum/BaseModel/dataclass) before instantiating it:
    #   1. never import a fresh module - only resolve from modules already loaded in this process.
    #      A value's class is always imported by the time we restore it, so this loses nothing
    #      legitimate while removing "import an attacker-named module for its import-time side
    #      effect" as a gadget.
    #   2. walk namespace __dict__ entries ONLY - never getattr - so no descriptor, property getter
    #      or module-level __getattr__ (PEP 562, often a lazy import) fires during resolution. This
    #      is what actually enforces "no code runs while resolving"; plain getattr does not.
    #   3. refuse dunder segments (__globals__, __class__, ...) so the walk cannot pivot out of the
    #      module/class namespace into a gadget chain.
    module_name, sep, qualname = dotted.partition(":")
    if not sep or not qualname:
        raise CodecError(f"malformed type tag {dotted!r}")
    module = sys.modules.get(module_name)
    if module is None:
        raise CodecError(f"refusing to import module {module_name!r} to decode a tagged value (not already loaded)")
    obj: Any = module
    for part in qualname.split("."):
        if part.startswith("__") or part == "":
            raise CodecError(f"refusing to traverse {part!r} in type tag {dotted!r}")
        namespace = getattr(obj, "__dict__", None)
        # a module's __dict__ is a plain dict; a class's is a mappingproxy; both are safe to read
        # without triggering attribute-access machinery. Anything without a readable __dict__
        # (or missing the key) is unresolvable by design rather than via a side-effecting getattr.
        if namespace is None or part not in namespace:
            raise CodecError(f"cannot resolve {part!r} of {dotted!r} without triggering attribute access")
        obj = namespace[part]
    return obj


# Optional decode-time type allow-list (#6 hardening). Empty = permissive: the JSON codec stays
# kind-gated only (enum/BaseModel/dataclass), which is the default and breaks nothing. Once a
# deployer/app registers any type via allow_decode_types(), decoding is additionally restricted to
# the registered "module:qualname" tags - closing the residual "a leaked secret lets a forged
# envelope construct ANY same-kind loaded class with attacker-controlled args" surface, for those
# who want the tighter boundary without forcing every persisted type to be registered.
_allowed_decode_types: set = set()


def allow_decode_types(*tags: str) -> None:
    """Restrict JSON-codec decoding of tagged enum/model/dataclass values to these ``module:qualname``
    types (e.g. ``"myapp.models:Renter"``). Additive; enforced as soon as any type is registered."""
    _allowed_decode_types.update(tags)


def _check_decode_allowed(tag: str) -> None:
    if _allowed_decode_types and tag not in _allowed_decode_types:
        raise CodecError(f"type {tag!r} is not in the state decode allow-list (set via solara.state.allow_decode_types)")


def _from_jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        marker = value.get(_MARKER)
        if marker is None:
            return {key: _from_jsonable(item) for key, item in value.items()}
        try:
            if marker == "set":
                return {_from_jsonable(item) for item in value["value"]}
            if marker == "frozenset":
                return frozenset(_from_jsonable(item) for item in value["value"])
            if marker == "datetime":
                return datetime.datetime.fromisoformat(value["value"])
            if marker == "date":
                return datetime.date.fromisoformat(value["value"])
            if marker == "time":
                return datetime.time.fromisoformat(value["value"])
            if marker == "uuid":
                return uuid.UUID(value["value"])
            if marker == "decimal":
                return decimal.Decimal(value["value"])
            if marker == "bytes":
                return base64.b64decode(value["value"])
            if marker == "enum":
                _check_decode_allowed(value["type"])
                enum_cls = _resolve(value["type"])
                # gate like the pydantic/dataclass branches below: a forged (but HMAC-valid)
                # tag must not turn into an arbitrary call. Without this, type="os:system"
                # would resolve os.system and call it with the attacker's "value" - RCE on the
                # default codec for anyone who holds the secret. Only ever call an Enum subclass.
                if not (isinstance(enum_cls, type) and issubclass(enum_cls, enum.Enum)):
                    raise CodecError(f"refusing to decode enum tag: {value['type']!r} is not an enum.Enum subclass")
                return enum_cls(_from_jsonable(value["value"]))
            if marker == "pydantic":
                _check_decode_allowed(value["type"])
                cls = _resolve(value["type"])
                import pydantic  # decoding a pydantic tag on an instance without pydantic -> ImportError -> CodecError

                # strict gate: only ever instantiate BaseModel subclasses - a forged (but
                # HMAC-valid) tag must not become an arbitrary-constructor call
                if not (isinstance(cls, type) and issubclass(cls, pydantic.BaseModel)):
                    raise CodecError(f"refusing to decode pydantic tag: {value['type']!r} is not a pydantic.BaseModel subclass")
                fields = _from_jsonable(value["value"])
                if hasattr(cls, "model_validate"):
                    return cls.model_validate(fields)
                return cls.parse_obj(fields)  # type: ignore[attr-defined]  # pydantic v1
            if marker == "dataclass":
                _check_decode_allowed(value["type"])
                cls = _resolve(value["type"])
                if not (isinstance(cls, type) and dataclasses.is_dataclass(cls)):
                    raise CodecError(f"refusing to decode dataclass tag: {value['type']!r} is not a dataclass")
                fields = {key: _from_jsonable(item) for key, item in value["value"].items()}
                return cls(**fields)
        except EnvelopeError:
            raise
        except Exception as exc:
            raise CodecError(f"failed to decode tagged value {marker!r}: {exc}") from exc
        raise CodecError(f"unknown tagged value {marker!r} in json envelope")
    if isinstance(value, list):
        return [_from_jsonable(item) for item in value]
    return value


def _json_dumps(value: Any) -> bytes:
    tree = _to_jsonable(value)
    try:
        return json.dumps(tree, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise SerializeError(f"json encoding failed: {exc}") from exc


def _json_loads(blob: bytes) -> Any:
    try:
        tree = json.loads(blob.decode("utf-8"))
    except ValueError as exc:
        raise CodecError(f"json decoding failed: {exc}") from exc
    return _from_jsonable(tree)


# --- pickle codec (deployer-gated) ----------------------------------------


def _require_pickle_allowed() -> None:
    if not solara.settings.state.allow_pickle:
        raise CodecError(
            "the 'pickle' codec is disabled. Set SOLARA_STATE_ALLOW_PICKLE=true to enable it. "
            "This is a deployer-side gate: pickle can execute arbitrary code on decode, so it must "
            "never be opted into by application or library code alone."
        )


def _pickle_dumps(value: Any) -> bytes:
    _require_pickle_allowed()
    try:
        return pickle.dumps(value)
    except Exception as exc:
        raise SerializeError(f"pickle encoding failed: {exc}") from exc


def _pickle_loads(blob: bytes) -> Any:
    _require_pickle_allowed()
    try:
        return pickle.loads(blob)
    except Exception as exc:
        raise CodecError(f"pickle decoding failed: {exc}") from exc


register_codec("json", _json_dumps, _json_loads)
register_codec("pickle", _pickle_dumps, _pickle_loads)


# --- secret keys and signing ----------------------------------------------


def _secret_keys() -> List[str]:
    keys = solara.settings.state.secret_key_list()
    if not keys:
        raise EnvelopeError("no state secret keys configured; set SOLARA_STATE_SECRET_KEYS")
    # Enforce the non-placeholder rule here, not only at server startup: an alternate/embedding
    # entry point that enables a backend without calling validate_state_settings would otherwise
    # sign/verify with the world-known "change me" key (collapsing the leaked-secret threat model
    # to "no leak required"). Refuse at the point of use.
    if any(key == "change me" for key in keys):
        raise EnvelopeError("SOLARA_STATE_SECRET_KEYS must not contain the placeholder value 'change me'")
    return keys


def _key_id(key: str) -> bytes:
    return hashlib.sha256(key.encode("utf-8")).digest()[:_KEY_ID_SIZE]


def _find_key(keys: List[str], key_id: bytes) -> Optional[str]:
    for key in keys:
        if hmac.compare_digest(_key_id(key), key_id):
            return key
    return None


def _canonical(key_id: bytes, kernel_id: str, field_name: str, codec: str, payload: bytes) -> bytes:
    # length-prefix every component so no concatenation is ambiguous
    parts = [key_id, kernel_id.encode("utf-8"), field_name.encode("utf-8"), codec.encode("utf-8"), payload]
    out = bytearray()
    for part in parts:
        out += len(part).to_bytes(4, "big")
        out += part
    return bytes(out)


def _sign(key: str, canonical: bytes) -> bytes:
    return hmac.new(key.encode("utf-8"), canonical, hashlib.sha256).digest()


# --- pack / unpack --------------------------------------------------------


def _pack(key_id: bytes, codec: str, payload: bytes, mac: bytes) -> bytes:
    codec_bytes = codec.encode("utf-8")
    out = bytearray()
    out.append(_FORMAT_VERSION)
    for part in (key_id, codec_bytes, payload):
        out += len(part).to_bytes(4, "big")
        out += part
    out += mac
    return bytes(out)


def _read_lp(blob: memoryview, offset: int) -> Tuple[bytes, int]:
    if offset + 4 > len(blob):
        raise ValueError("truncated length prefix")
    length = int.from_bytes(blob[offset : offset + 4], "big")
    offset += 4
    if offset + length > len(blob):
        raise ValueError("length exceeds buffer")
    return bytes(blob[offset : offset + length]), offset + length


def _unpack(blob: bytes) -> Tuple[int, bytes, str, bytes, bytes]:
    view = memoryview(blob)
    if len(view) < 1:
        raise ValueError("empty envelope")
    version = view[0]
    offset = 1
    key_id, offset = _read_lp(view, offset)
    codec_bytes, offset = _read_lp(view, offset)
    payload, offset = _read_lp(view, offset)
    mac = bytes(view[offset:])
    if len(mac) != _HMAC_SIZE:
        raise ValueError("truncated or trailing bytes after payload")
    return version, key_id, codec_bytes.decode("utf-8"), payload, mac


# --- public API -----------------------------------------------------------


def encode(value: Any, *, codec: str = "json", kernel_id: str, field_name: str) -> bytes:
    """Serialize `value` with `codec` and wrap it in a signed envelope bound to `kernel_id`/`field_name`."""
    dumps, _ = _get_codec(codec)
    keys = _secret_keys()
    primary = keys[0]
    key_id = _key_id(primary)
    try:
        payload = dumps(value)
    except SerializeError as exc:
        raise SerializeError(f"{exc} (field {field_name!r})") from exc
    canonical = _canonical(key_id, kernel_id, field_name, codec, payload)
    mac = _sign(primary, canonical)
    return _pack(key_id, codec, payload, mac)


def decode(blob: bytes, *, kernel_id: str, field_name: str) -> Any:
    """Verify the envelope (HMAC first) then decode its payload, checking `kernel_id`/`field_name` binding."""
    try:
        version, key_id, codec, payload, mac = _unpack(blob)
    except (ValueError, IndexError) as exc:
        raise EnvelopeError(f"malformed envelope for field {field_name!r}: {exc}") from exc
    if version != _FORMAT_VERSION:
        raise EnvelopeError(f"unsupported envelope format version {version} for field {field_name!r}")
    keys = _secret_keys()
    key = _find_key(keys, key_id)
    if key is None:
        raise HmacError(f"no configured secret key matches the envelope for field {field_name!r}")
    expected = _sign(key, _canonical(key_id, kernel_id, field_name, codec, payload))
    if not hmac.compare_digest(expected, mac):
        raise HmacError(f"HMAC verification failed for field {field_name!r} (tampered, wrong key, or replayed across kernel/field)")
    _, loads = _get_codec(codec)
    return loads(payload)


def session_hmac(session_id: str) -> bytes:
    """HMAC-SHA-256 of ``session_id`` with the PRIMARY key - the value written on flush (sign-first)."""
    return _sign(_secret_keys()[0], session_id.encode("utf-8"))


def session_hmacs(session_id: str) -> List[bytes]:
    """All acceptable session HMACs (one per configured key), primary first - the verify-ANY set
    used by takeover identity checks.

    The session-ownership token must be key-rotation safe exactly like the envelope MAC: without
    this, promoting a new primary key makes ``session_hmac`` (primary-only) stop matching every
    ``__session_id__`` written by the old primary, so every in-flight persisted kernel fails the
    identity check and its state is orphaned - a fleet-wide loss of recovery caused by the very
    rotation the feature exists to support. Takeover accepts a match against ANY key; the next
    flush rewrites ``__session_id__`` with the primary, migrating it forward.
    """
    return [_sign(key, session_id.encode("utf-8")) for key in _secret_keys()]
