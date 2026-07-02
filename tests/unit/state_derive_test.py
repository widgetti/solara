"""Tests for solara.state.derive: the persistence-key derivation refusal matrix.

Because ``executing`` needs real source on disk, most cases are generated as small
modules in a temp dir and imported. Each generated module calls ``_fake_reactive(...)``
from a generated support module; the support module calls ``derive_key()``. The support
module is made "internal" (via monkeypatching ``_is_internal_module``) so the frame walk
lands on the assignment site in the generated module rather than the support helper.
"""

import gc
import importlib
import os
import sys
import textwrap

import pytest

import solara.toestand as toestand
from solara.state import derive
from solara.state.derive import PersistKeyError


class _Dummy:
    # plain object() does not support weakref; the registry needs a weakref-able target
    pass


@pytest.fixture
def env(tmp_path, monkeypatch):
    src_dir = str(tmp_path)
    monkeypatch.syspath_prepend(src_dir)

    support_path = os.path.join(src_dir, "_fake_support_mod.py")
    with open(support_path, "w") as f:
        f.write("from solara.state.derive import derive_key\n\ndef _fake_reactive(value):\n    return derive_key()\n")
    support_abspath = os.path.abspath(support_path)

    orig_is_internal = toestand._is_internal_module

    def patched_is_internal(file_name):
        if os.path.abspath(file_name) == support_abspath:
            return True
        return orig_is_internal(file_name)

    # derive.py imported the name directly; patch both references
    monkeypatch.setattr(toestand, "_is_internal_module", patched_is_internal)
    monkeypatch.setattr(derive, "_is_internal_module", patched_is_internal)

    import _fake_support_mod  # noqa: F401

    created = ["_fake_support_mod"]
    counter = {"n": 0}

    def make_module(body):
        counter["n"] += 1
        name = f"_gen_mod_{counter['n']}"
        path = os.path.join(src_dir, name + ".py")
        with open(path, "w") as f:
            f.write("from _fake_support_mod import _fake_reactive\n")
            f.write(textwrap.dedent(body).lstrip("\n"))
        created.append(name)
        return importlib.import_module(name)

    derive._reset_registry()
    yield type("Env", (), {"make_module": staticmethod(make_module), "support": _fake_support_mod})
    derive._reset_registry()
    for name in created:
        sys.modules.pop(name, None)


# --- accepted shapes --------------------------------------------------------------------


def test_single_name_assignment(env):
    mod = env.make_module("count = _fake_reactive(0)")
    assert mod.count == f"{mod.__name__}:count"


def test_annotated_assignment(env):
    mod = env.make_module("n: int = _fake_reactive(0)")
    assert mod.n == f"{mod.__name__}:n"


# --- refused shapes ---------------------------------------------------------------------


def test_multi_target_refused(env):
    with pytest.raises(PersistKeyError) as exc:
        env.make_module("a = b = _fake_reactive(0)")
    assert "chained assignment" in str(exc.value)


def test_tuple_unpack_refused(env):
    with pytest.raises(PersistKeyError) as exc:
        env.make_module("x, y = _fake_reactive(0), 1")
    assert "tuple" in str(exc.value).lower()


def test_container_position_refused(env):
    with pytest.raises(PersistKeyError) as exc:
        env.make_module("items = [_fake_reactive(0)]")
    assert "container" in str(exc.value) or "not assigned" in str(exc.value)


def test_call_argument_refused(env):
    with pytest.raises(PersistKeyError) as exc:
        env.make_module("result = print(_fake_reactive(0))")
    assert "not assigned" in str(exc.value)


def test_attribute_target_refused(env):
    body = """
    class _Holder:
        pass
    obj = _Holder()
    obj.attr = _fake_reactive(0)
    """
    with pytest.raises(PersistKeyError) as exc:
        env.make_module(body)
    assert "attribute" in str(exc.value)


def test_inside_function_refused(env):
    body = """
    def factory():
        q = _fake_reactive(0)
        return q
    made = factory()
    """
    with pytest.raises(PersistKeyError) as exc:
        env.make_module(body)
    msg = str(exc.value)
    assert "function or factory" in msg
    assert 'key=f"' in msg
    assert "NEVER use a constant key" in msg


def test_inside_loop_refused(env):
    body = """
    for _ in range(1):
        looped = _fake_reactive(0)
    """
    with pytest.raises(PersistKeyError) as exc:
        env.make_module(body)
    assert "loop" in str(exc.value)


def test_inside_conditional_refused(env):
    body = """
    if True:
        conditioned = _fake_reactive(0)
    """
    with pytest.raises(PersistKeyError) as exc:
        env.make_module(body)
    assert "conditional" in str(exc.value)


def test_class_body_refused_but_hints_class_attribute(env):
    body = """
    class C:
        x = _fake_reactive(0)
    """
    with pytest.raises(PersistKeyError) as exc:
        env.make_module(body)
    assert "class body" in str(exc.value)
    assert "__set_name__" in str(exc.value)


def test_no_source_refused(env):
    # exec'd code has no linecache entry, so executing cannot resolve the node
    code = "count = _fake_reactive(0)"
    g = {"_fake_reactive": env.support._fake_reactive}
    with pytest.raises(PersistKeyError) as exc:
        exec(compile(code, "<generated-no-source>", "exec"), g)
    assert "source" in str(exc.value).lower()


# --- class-attribute key derivation -------------------------------------------------------


class _OwnerForKey:
    pass


def test_derive_key_for_class_attribute():
    key = derive.derive_key_for_class_attribute(_OwnerForKey, "x")
    assert key == f"{__name__}:_OwnerForKey.x"


# --- message quality --------------------------------------------------------------------


def test_message_quality(env):
    body = """
    def factory():
        q = _fake_reactive(0)
        return q
    made = factory()
    """
    with pytest.raises(PersistKeyError) as exc:
        env.make_module(body)
    msg = str(exc.value)
    # filename + lineno present
    assert "_gen_mod_" in msg
    assert ".py:" in msg
    # source line present
    assert "_fake_reactive(0)" in msg
    # fix example present
    assert 'solara.reactive(..., persist=True, key=f"user:{user_id}:query")' in msg


# --- collision registry -----------------------------------------------------------------


def test_registry_collision_names_both_sites():
    derive._reset_registry()
    a, b = _Dummy(), _Dummy()
    src_a = ("app/state.py", 10, 0)
    src_b = ("app/other.py", 42, 4)
    derive.register_persist_key("myapp:count", a, src_a, derived=True)
    with pytest.raises(PersistKeyError) as exc:
        derive.register_persist_key("myapp:count", b, src_b, derived=True)
    msg = str(exc.value)
    assert "app/state.py:10" in msg
    assert "app/other.py:42" in msg
    assert "myapp:count" in msg
    derive._reset_registry()


def test_registry_same_source_reregistration_ok():
    derive._reset_registry()
    a, b = _Dummy(), _Dummy()
    src = ("app/state.py", 10, 0)
    derive.register_persist_key("myapp:count", a, src, derived=True)
    # hot reload re-executes the module: new object, identical source -> allowed
    derive.register_persist_key("myapp:count", b, src, derived=True)
    derive._reset_registry()


def test_registry_dead_weakref_reuse_ok():
    derive._reset_registry()
    a = _Dummy()
    src_a = ("app/state.py", 10, 0)
    derive.register_persist_key("myapp:count", a, src_a, derived=True)
    del a
    gc.collect()
    b = _Dummy()
    src_b = ("app/other.py", 99, 0)
    # previous holder is dead -> different source is fine now
    derive.register_persist_key("myapp:count", b, src_b, derived=True)
    derive._reset_registry()


def test_registry_explicit_keys_also_protected():
    derive._reset_registry()
    a, b = _Dummy(), _Dummy()
    derive.register_persist_key("explicit", a, ("a.py", 1, 0), derived=False)
    with pytest.raises(PersistKeyError):
        derive.register_persist_key("explicit", b, ("b.py", 2, 0), derived=False)
    derive._reset_registry()
