import datetime
import decimal
import enum
import uuid

import pytest

import solara.settings
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
    monkeypatch.setattr(solara.settings.state, "secret_keys", "primary-test-key")
    monkeypatch.setattr(solara.settings.state, "allow_pickle", False)


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
    monkeypatch.setattr(solara.settings.state, "secret_keys", "oldkey")
    old_blob = state.encode({"x": 1}, kernel_id="k", field_name="f")
    # add-new-verify-only: new key goes first (becomes the signer) but the old still verifies
    monkeypatch.setattr(solara.settings.state, "secret_keys", "newkey,oldkey")
    assert state.decode(old_blob, kernel_id="k", field_name="f") == {"x": 1}
    new_blob = state.encode({"y": 2}, kernel_id="k", field_name="f")
    assert state.decode(new_blob, kernel_id="k", field_name="f") == {"y": 2}
    # both verify simultaneously
    assert state.decode(old_blob, kernel_id="k", field_name="f") == {"x": 1}


def test_dropping_signing_key_invalidates_its_envelopes(monkeypatch):
    monkeypatch.setattr(solara.settings.state, "secret_keys", "oldkey")
    old_blob = state.encode({"x": 1}, kernel_id="k", field_name="f")
    monkeypatch.setattr(solara.settings.state, "secret_keys", "brandnew")
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
    monkeypatch.setattr(solara.settings.state, "allow_pickle", False)
    with pytest.raises(CodecError) as excinfo:
        state.encode({"x": 1}, codec="pickle", kernel_id="k", field_name="f")
    assert "SOLARA_STATE_ALLOW_PICKLE" in str(excinfo.value)


def test_pickle_gate_on_roundtrips_then_decode_refuses_when_flipped_off(monkeypatch):
    monkeypatch.setattr(solara.settings.state, "allow_pickle", True)
    blob = state.encode({"z": 3}, codec="pickle", kernel_id="k", field_name="f")
    assert state.decode(blob, kernel_id="k", field_name="f") == {"z": 3}
    monkeypatch.setattr(solara.settings.state, "allow_pickle", False)
    with pytest.raises(CodecError):
        state.decode(blob, kernel_id="k", field_name="f")


def test_missing_secret_keys_raises(monkeypatch):
    monkeypatch.setattr(solara.settings.state, "secret_keys", "")
    with pytest.raises(EnvelopeError):
        state.encode({"x": 1}, kernel_id="k", field_name="f")


def test_session_hmac_deterministic_and_key_dependent(monkeypatch):
    monkeypatch.setattr(solara.settings.state, "secret_keys", "keyA")
    first = state.session_hmac("session-123")
    assert first == state.session_hmac("session-123")
    assert first != state.session_hmac("session-456")
    assert len(first) == 32
    monkeypatch.setattr(solara.settings.state, "secret_keys", "keyB")
    assert first != state.session_hmac("session-123")


def test_register_custom_codec():
    state.register_codec("reverse", lambda v: v[::-1], lambda b: b[::-1])
    try:
        blob = state.encode(b"abc", codec="reverse", kernel_id="k", field_name="f")
        assert state.decode(blob, kernel_id="k", field_name="f") == b"abc"
    finally:
        from solara.state import envelope

        envelope._CODECS.pop("reverse", None)
