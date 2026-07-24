import datetime
import decimal
import enum
import uuid
from typing import List

import pytest

import solara.server.settings
import solara.state as state
from solara.state import CodecError, EnvelopeError, HmacError, SerializeError


class Color(enum.Enum):
    RED = "red"
    BLUE = "blue"


class Size(enum.IntEnum):
    SMALL = 1
    LARGE = 2


@pytest.fixture(autouse=True)
def _secret_keys(monkeypatch):
    monkeypatch.setattr(solara.server.settings.state, "secret_keys", "primary-test-key")
    monkeypatch.setattr(solara.server.settings.state, "allow_pickle", False)


def roundtrip(value, codec="json", kernel_id="kern", field_name="field"):
    blob = state.encode(value, codec=codec, kernel_id=kernel_id, field_name=field_name)
    return state.decode(blob, kernel_id=kernel_id, field_name=field_name)


@pytest.mark.parametrize(
    "value",
    [
        None,
        True,
        False,
        0,
        42,
        -3.14,
        "hello",
        [1, 2, "three"],
        {"a": 1, "b": [2, 3]},
        {"nested": {"deep": [{"x": 1}]}},
        datetime.datetime(2020, 1, 2, 3, 4, 5, 678),
        datetime.date(2021, 5, 6),
        datetime.time(1, 2, 3),
        Color.RED,
        Color.BLUE,
        Size.LARGE,
        uuid.UUID("12345678-1234-5678-1234-567812345678"),
        decimal.Decimal("1.500"),
        {1, 2, 3},
        frozenset([4, 5, 6]),
        b"raw bytes \x00\x01",
    ],
)
def test_roundtrip_coercions(value):
    result = roundtrip(value)
    assert result == value
    assert type(result) is type(value)


def test_roundtrip_enum_identity():
    assert roundtrip(Color.RED) is Color.RED
    assert roundtrip(Size.LARGE) is Size.LARGE


def test_roundtrip_nested_container_of_types():
    value = {
        "when": datetime.datetime(2020, 1, 1),
        "color": Color.BLUE,
        "ids": {uuid.UUID(int=1), uuid.UUID(int=2)},
        "amount": decimal.Decimal("9.99"),
        "blob": b"\xff\x00",
    }
    result = roundtrip(value)
    assert result == value


def test_tuple_roundtrips_to_list():
    # documented JSON caveat: tuples come back as lists
    assert roundtrip((1, 2, 3)) == [1, 2, 3]


def test_numpy_scalars_coerced_to_python():
    numpy = pytest.importorskip("numpy")
    assert roundtrip(numpy.int64(7)) == 7
    assert type(roundtrip(numpy.int64(7))) is int
    assert roundtrip(numpy.float64(1.5)) == 1.5
    assert type(roundtrip(numpy.float64(1.5))) is float


def test_tamper_hmac_region_raises_hmac_error():
    from solara.state import envelope

    blob = state.encode({"secret": 1}, kernel_id="k", field_name="f")
    # flipping any byte of the trailing HMAC must be caught by verification, not parsing
    for pos in range(len(blob) - envelope._HMAC_SIZE, len(blob)):
        tampered = bytearray(blob)
        tampered[pos] ^= 0x01
        with pytest.raises(HmacError):
            state.decode(bytes(tampered), kernel_id="k", field_name="f")


def test_tamper_anywhere_is_detected():
    blob = state.encode({"secret": 1}, kernel_id="k", field_name="f")
    for pos in range(len(blob)):
        tampered = bytearray(blob)
        tampered[pos] ^= 0xFF
        with pytest.raises(EnvelopeError):
            state.decode(bytes(tampered), kernel_id="k", field_name="f")


def test_cross_kernel_replay_rejected():
    blob = state.encode({"x": 1}, kernel_id="kernel-a", field_name="f")
    with pytest.raises(HmacError):
        state.decode(blob, kernel_id="kernel-b", field_name="f")


def test_cross_field_replay_rejected():
    blob = state.encode({"x": 1}, kernel_id="k", field_name="field-a")
    with pytest.raises(HmacError):
        state.decode(blob, kernel_id="k", field_name="field-b")


def test_key_rotation_add_new_key_first(monkeypatch):
    monkeypatch.setattr(solara.server.settings.state, "secret_keys", "oldkey")
    old_blob = state.encode({"x": 1}, kernel_id="k", field_name="f")
    # add-new-verify-only: new key goes first (becomes the signer) but the old still verifies
    monkeypatch.setattr(solara.server.settings.state, "secret_keys", "newkey,oldkey")
    assert state.decode(old_blob, kernel_id="k", field_name="f") == {"x": 1}
    new_blob = state.encode({"y": 2}, kernel_id="k", field_name="f")
    assert state.decode(new_blob, kernel_id="k", field_name="f") == {"y": 2}
    # both verify simultaneously
    assert state.decode(old_blob, kernel_id="k", field_name="f") == {"x": 1}


def test_dropping_signing_key_invalidates_its_envelopes(monkeypatch):
    monkeypatch.setattr(solara.server.settings.state, "secret_keys", "oldkey")
    old_blob = state.encode({"x": 1}, kernel_id="k", field_name="f")
    monkeypatch.setattr(solara.server.settings.state, "secret_keys", "brandnew")
    with pytest.raises(HmacError):
        state.decode(old_blob, kernel_id="k", field_name="f")


def test_unknown_type_raises_serialize_error_naming_type_and_field():
    class Widget:
        pass

    with pytest.raises(SerializeError) as excinfo:
        state.encode(Widget(), kernel_id="k", field_name="my_field")
    message = str(excinfo.value)
    assert "Widget" in message
    assert "my_field" in message


def test_unknown_codec_raises_codec_error():
    with pytest.raises(CodecError):
        state.encode(1, codec="does-not-exist", kernel_id="k", field_name="f")


def test_pickle_gate_off_refuses_encode_and_decode(monkeypatch):
    monkeypatch.setattr(solara.server.settings.state, "allow_pickle", False)
    with pytest.raises(CodecError) as excinfo:
        state.encode({"x": 1}, codec="pickle", kernel_id="k", field_name="f")
    assert "SOLARA_STATE_ALLOW_PICKLE" in str(excinfo.value)


def test_pickle_gate_on_roundtrips_then_decode_refuses_when_flipped_off(monkeypatch):
    monkeypatch.setattr(solara.server.settings.state, "allow_pickle", True)
    blob = state.encode({"z": 3}, codec="pickle", kernel_id="k", field_name="f")
    assert state.decode(blob, kernel_id="k", field_name="f") == {"z": 3}
    monkeypatch.setattr(solara.server.settings.state, "allow_pickle", False)
    with pytest.raises(CodecError):
        state.decode(blob, kernel_id="k", field_name="f")


def test_missing_secret_keys_raises(monkeypatch):
    monkeypatch.setattr(solara.server.settings.state, "secret_keys", "")
    with pytest.raises(EnvelopeError):
        state.encode({"x": 1}, kernel_id="k", field_name="f")


def test_session_hmac_deterministic_and_key_dependent(monkeypatch):
    monkeypatch.setattr(solara.server.settings.state, "secret_keys", "keyA")
    first = state.session_hmac("session-123")
    assert first == state.session_hmac("session-123")
    assert first != state.session_hmac("session-456")
    assert len(first) == 32
    monkeypatch.setattr(solara.server.settings.state, "secret_keys", "keyB")
    assert first != state.session_hmac("session-123")


def test_register_custom_codec():
    state.register_codec("reverse", lambda v: v[::-1], lambda b: b[::-1])
    try:
        blob = state.encode(b"abc", codec="reverse", kernel_id="k", field_name="f")
        assert state.decode(blob, kernel_id="k", field_name="f") == b"abc"
    finally:
        from solara.state import envelope

        envelope._CODECS.pop("reverse", None)


# --- structured types: pydantic models and dataclasses (self-describing tags) --------------
#
# The class travels with the value (module:qualname), so deserialization needs no target
# class declared anywhere - reactive(None, persist=True) works when a model lands in it
# later. Decode gates on issubclass(BaseModel)/is_dataclass before instantiating.

import dataclasses  # noqa: E402

import pydantic  # noqa: E402


class User(pydantic.BaseModel):
    name: str
    color: Color = Color.RED
    joined: datetime.date = datetime.date(2020, 1, 2)


class Team(pydantic.BaseModel):
    lead: User
    members: List["User"]  # typing.List: py3.8 cannot evaluate builtin subscripting in annotations
    tags: list = []


@dataclasses.dataclass
class Point:
    x: int
    y: int


@dataclasses.dataclass
class Path:
    label: str
    points: list
    start: "Point" = dataclasses.field(default_factory=lambda: Point(0, 0))
    length: int = dataclasses.field(init=False, default=0)

    def __post_init__(self):
        self.length = len(self.points)


def test_pydantic_model_roundtrip():
    user = User(name="ada", color=Color.BLUE, joined=datetime.date(2021, 3, 4))
    result = roundtrip(user)
    assert isinstance(result, User)
    assert result == user
    assert result.color is Color.BLUE
    assert result.joined == datetime.date(2021, 3, 4)


def test_pydantic_nested_model_and_container_roundtrip():
    team = Team(lead=User(name="ada"), members=[User(name="bob", color=Color.BLUE)])
    result = roundtrip({"team": team, "count": 2})
    assert isinstance(result["team"], Team)
    assert isinstance(result["team"].lead, User)
    # typed fields reconstruct nested models: the codec matches pydantic's own
    # dump/validate round-trip semantics exactly
    assert result["team"].members[0].color is Color.BLUE


def test_pydantic_untyped_container_matches_pydantic_semantics():
    # an untyped `list` field means "list of anything" to pydantic: its own
    # model_validate(model_dump()) round-trip leaves nested models as dicts, and so do we
    team = Team(lead=User(name="ada"), members=[], tags=[User(name="bob")])
    pydantic_roundtrip = Team.model_validate(team.model_dump())
    ours = roundtrip(team)
    assert isinstance(pydantic_roundtrip.tags[0], dict)
    assert isinstance(ours.tags[0], dict)
    assert ours.tags[0]["name"] == "bob"


def test_dataclass_roundtrip_nested_with_post_init():
    path = Path(label="route", points=[Point(1, 2), Point(3, 4)])
    result = roundtrip(path)
    assert isinstance(result, Path)
    assert result == path
    assert isinstance(result.points[0], Point)
    # init=False fields are not stored: recomputed by __post_init__
    assert result.length == 2


def test_none_roundtrips_without_class_knowledge():
    # the Optional[Model]-with-None-default case: None needs no tag, a later model tags itself
    assert roundtrip(None) is None
    assert roundtrip(User(name="ada")) == User(name="ada")


def test_decode_gate_refuses_non_model_class():
    from solara.state.envelope import _from_jsonable

    with pytest.raises(CodecError, match="not a pydantic.BaseModel"):
        _from_jsonable({"__solara_type__": "pydantic", "type": "builtins:dict", "value": {}})
    with pytest.raises(CodecError, match="not a dataclass"):
        _from_jsonable({"__solara_type__": "dataclass", "type": "builtins:dict", "value": {}})


def test_enum_tag_refuses_non_enum_class_no_rce():
    # the class-tag decoder must never turn an HMAC-valid tag into an arbitrary call: without
    # the enum gate, type="os:system" resolved os.system and called it (RCE on the default
    # codec for anyone holding the secret). Every non-enum callable must be refused.
    from solara.state.envelope import _from_jsonable

    with pytest.raises(CodecError, match="not an enum.Enum subclass"):
        _from_jsonable({"__solara_type__": "enum", "type": "os:system", "value": "echo pwned"})
    with pytest.raises(CodecError, match="not an enum.Enum subclass"):
        _from_jsonable({"__solara_type__": "enum", "type": "builtins:print", "value": "x"})
    # end to end through a real signed envelope: a forged (valid-HMAC) enum tag decodes to an
    # error, never a call
    import os

    sentinel = f"/tmp/solara_enum_rce_{os.getpid()}"
    if os.path.exists(sentinel):
        os.remove(sentinel)
    # forge a valid-HMAC os.system payload with the (test) secret the attacker is assumed to hold
    import json

    from solara.state import envelope

    payload = json.dumps({"__solara_type__": "enum", "type": "os:system", "value": f"touch {sentinel}"}).encode()
    key = envelope._secret_keys()[0]
    key_id = envelope._key_id(key)
    mac = envelope._sign(key, envelope._canonical(key_id, "k", "f", "json", payload))
    forged = envelope._pack(key_id, "json", payload, mac)
    with pytest.raises(CodecError):
        state.decode(forged, kernel_id="k", field_name="f")
    assert not os.path.exists(sentinel), "enum gate bypassed: os.system ran during decode"


def test_resolve_refuses_not_already_imported_module():
    # _resolve never imports a fresh module: importing an attacker-named module for its
    # import-time side effect is not a gadget. The class of any real value is already imported
    # by restore time, so this loses nothing legitimate.
    from solara.state.envelope import _from_jsonable

    with pytest.raises(CodecError, match="not already loaded"):
        _from_jsonable({"__solara_type__": "dataclass", "type": "antigravity:x", "value": {}})


def test_resolve_does_not_fire_descriptors_during_walk():
    # #5: a forged tag must not run a property getter / module __getattr__ while RESOLVING. The
    # descriptor-safe walk (via __dict__) refuses to traverse into an instance attribute that would
    # otherwise fire a getter, so the side effect never happens.
    import sys as _sys
    from solara.state.envelope import _from_jsonable

    module = type(_sys)("evil_gadget_mod")
    fired = {"count": 0}

    class WithSideEffect:
        @property
        def boom(self):  # a property getter that must NEVER run during resolution
            fired["count"] += 1
            return __import__("os").getcwd

    setattr(module, "singleton", WithSideEffect())
    _sys.modules["evil_gadget_mod"] = module
    try:
        with pytest.raises(CodecError):
            _from_jsonable({"__solara_type__": "enum", "type": "evil_gadget_mod:singleton.boom", "value": 0})
        assert fired["count"] == 0  # the getter never ran
    finally:
        del _sys.modules["evil_gadget_mod"]


def test_decode_allow_list_rejects_unregistered_types():
    # #6: with an allow-list configured, decoding a same-kind class not on the list is refused.
    import solara.state as state
    from solara.state.envelope import _from_jsonable, _to_jsonable, _allowed_decode_types

    tree = _to_jsonable(Color.RED)  # a legit enum value from this test module
    tag = tree["type"]
    try:
        state.allow_decode_types("some.other:Type")  # non-empty, but not our tag -> enforced
        with pytest.raises(CodecError, match="not in the state decode allow-list"):
            _from_jsonable(tree)
        state.allow_decode_types(tag)  # now allow it -> round-trips again
        assert _from_jsonable(tree) == Color.RED
    finally:
        _allowed_decode_types.clear()


def test_renamed_class_fails_loud_not_silent():
    from solara.state.envelope import _from_jsonable

    # a class renamed/removed within a still-loaded module: the descriptor-safe resolve refuses to
    # find it (walks __dict__, never getattr) -> loud CodecError
    with pytest.raises(CodecError, match="cannot resolve"):
        _from_jsonable({"__solara_type__": "dataclass", "type": f"{__name__}:GoneAfterRename", "value": {}})
    # a class whose whole module is gone (module rename): also loud, via the not-loaded gate
    with pytest.raises(CodecError, match="not already loaded"):
        _from_jsonable({"__solara_type__": "dataclass", "type": "tests_no_such_module:Gone", "value": {}})


def test_model_shape_skew_fails_loud():
    # a required field added after the envelope was written -> validation error -> CodecError
    from solara.state.envelope import _from_jsonable, _to_jsonable

    tree = _to_jsonable(User(name="ada"))
    del tree["value"]["name"]
    with pytest.raises(CodecError, match="failed to decode tagged value"):
        _from_jsonable(tree)


def test_reserved_marker_key_in_dict_rejected_at_encode():
    with pytest.raises(SerializeError, match="reserved"):
        state.encode({"__solara_type__": "x"}, kernel_id="kern", field_name="field")


def test_non_string_dict_key_rejected_at_encode():
    with pytest.raises(SerializeError, match="dict keys must be str"):
        state.encode({1: "a"}, kernel_id="kern", field_name="field")


def test_containers_of_models_roundtrip():
    # every element is individually tagged (self-describing at every level), so bare
    # containers of models reconstruct real instances - no outer schema needed
    users = [User(name="a"), User(name="b", color=Color.BLUE)]
    result = roundtrip(users)
    assert [type(u) for u in result] == [User, User]
    assert result[1].color is Color.BLUE
    # tuples of models come back as LISTS of models (the documented tuple caveat)
    result = roundtrip((User(name="a"), User(name="b")))
    assert isinstance(result, list)
    assert [type(u) for u in result] == [User, User]
    # arbitrary nesting reconstructs too
    assert type(roundtrip({"team": [{"lead": User(name="x")}]})["team"][0]["lead"]) is User


def test_untyped_dataclass_field_reconstructs_models_unlike_pydantic():
    # asymmetry worth pinning: dataclass fields are tagged by OUR recursion (element by
    # element), so even an UNTYPED dataclass field reconstructs models - whereas an untyped
    # pydantic field goes through model_dump() first, which flattens models to dicts
    # (test_pydantic_untyped_container_matches_pydantic_semantics pins that side)
    @dataclasses.dataclass
    class Box:
        items: list

    import sys

    Box.__qualname__ = "Box"
    setattr(sys.modules[__name__], "Box", Box)
    Box.__module__ = __name__

    result = roundtrip(Box(items=[User(name="a")]))
    assert type(result.items[0]) is User
