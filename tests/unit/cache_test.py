import sys
from typing import Any, Dict

import ipyvuetify as v
import pytest

try:
    import redis
except ImportError:
    redis = None

import solara
import solara.cache

from .common import click

some_global = 1


def test_lru():
    c = solara.cache.Memory(max_items=2)
    c["a"] = 1
    c["b"] = 2
    c["c"] = 3
    assert "a" not in c
    assert "b" in c
    assert "c" in c
    c["b"] = 4
    assert "b" in c
    c["d"] = 5
    assert "c" not in c
    assert "b" in c
    assert "d" in c


def test_memoized_basic():
    c = solara.cache.Memory(max_items=2)

    @solara.cache.memoize(storage=c)
    def f(x: int) -> int:
        return x**2

    assert f(1) == 1
    assert f(2) == 4
    assert list(c.values()) == [1, 4]
    assert f(3) == 9
    assert list(c.values()) == [4, 9]


def test_memoized_nonlocals():
    c = solara.cache.Memory(max_items=2)

    some_nonlocal = 1

    @solara.cache.memoize(storage=c, allow_nonlocals=True)
    def f1(x: int) -> int:
        return x**2 + some_nonlocal

    assert f1(2) == 5
    # although some_nonlocal is changed, the cache is not invalidated
    # which means we get the same answer, while some_nonlocal has changed
    some_nonlocal = 10
    assert f1(2) == 5

    with pytest.raises(ValueError):

        @solara.cache.memoize(storage=c)
        def f2(x: int) -> int:
            return x**2 + some_nonlocal


def test_memoized_changing_globals():
    global some_global
    c = solara.cache.Memory(max_items=2)
    with pytest.raises(ValueError):
        # by changing a global, the memoize decorator should fail
        for value in [1, 10]:
            some_global = value

            @solara.cache.memoize(storage=c)
            def g(x: int) -> int:
                return x**2 + some_global

    @solara.cache.memoize(storage=c)
    def h(x: int) -> int:
        return x**2 + some_global

    with pytest.raises(ValueError):
        h(1)
        # by changing a global, the memoized function should fail
        some_global = 20
        h(2)


def test_memoized_naked():
    # no arguments to the decorator
    @solara.cache.memoize
    def f(x: int) -> int:
        return x**2

    f.storage.clear()
    assert f(1) == 1
    assert f(2) == 4
    assert list(f.storage.values()) == [1, 4]
    assert f(3) == 9
    assert list(f.storage.values()) == [1, 4, 9]


def test_memoized_custom_key():
    c = solara.cache.Memory(max_items=2)

    def mykey(x: int) -> str:
        return f"{-x}"

    @solara.cache.memoize(storage=c, key=mykey)
    def f(x: int) -> str:
        return f"{x**2}"

    assert f(1) == "1"
    assert f(2) == "4"
    assert [k[-1] for k in list(c.keys())] == ["-1", "-2"]
    assert list(c.values()) == ["1", "4"]
    assert f(3) == "9"
    assert list(c.values()) == ["4", "9"]
    assert [k[-1] for k in list(c.keys())] == ["-2", "-3"]


def test_memoized_similar_function_name():
    # if we share the cache between two functions with the same name, but different
    # implementations, we should get the correct results
    # this means the there should be something unique in the key related to the function
    @solara.cache.memoize
    def f(x: int) -> int:  # type: ignore
        return x**2

    f1 = f
    del f

    @solara.cache.memoize  # type: ignore
    def f(x: int) -> int:  # type: ignore
        return -(x**2)

    f2 = f

    assert f1(2) == 4
    assert f2(2) == -4


def test_cache_disk(tmpdir):
    path = tmpdir.join("cache")
    c = solara.cache.create("disk", path=str(path), clear=True)
    c["a"] = 1
    assert c["a"] == 1
    assert len(c) == 1
    del c["a"]
    assert "a" not in c
    assert len(c) == 0

    @solara.cache.memoize(storage=c)
    def f(*args, **kwargs):
        return args, kwargs

    # non trivial arguments
    assert f(1, 2, 3, a=1, b=2) == ((1, 2, 3), {"a": 1, "b": 2})
    assert f(1, 2, 3, a=1, b=2, c=3) == ((1, 2, 3), {"a": 1, "b": 2, "c": 3})
    assert f(1, 2, 3, a=1, b=2) == ((1, 2, 3), {"a": 1, "b": 2})
    assert len(c) == 2


@pytest.mark.skipif(condition=redis is None or sys.platform.startswith("win"), reason="redis not installed")
def test_cache_redis(tmpdir):
    c = solara.cache.create("redis", clear=True, prefix=b"solara-test:cache:")
    c["a"] = 1
    assert c["a"] == 1
    assert len(c) == 1
    del c["a"]
    assert "a" not in c
    assert len(c) == 0

    @solara.cache.memoize(storage=c)
    def f(*args, **kwargs):
        return args, kwargs

    # non trivial arguments
    assert f(1, 2, 3, a=1, b=2) == ((1, 2, 3), {"a": 1, "b": 2})
    assert f(1, 2, 3, a=1, b=2, c=3) == ((1, 2, 3), {"a": 1, "b": 2, "c": 3})
    assert f(1, 2, 3, a=1, b=2) == ((1, 2, 3), {"a": 1, "b": 2})
    assert len(c) == 2


def test_cache_memory_size():
    c = solara.cache.create("memory-size", max_size="100b")
    b40 = b"0123456789" * 2  # when pickled ~40 bytes (on py36 less)
    b80 = b40 * 3  # when pickled ~80 bytes
    c["a"] = b40
    c["b"] = b40
    assert list(c.keys()) == [b"a", b"b"]
    c["c"] = b80
    assert list(c.keys()) == [b"c"]

    # test non trivial keys
    c[(1, 2, {"a"})] = b40
    c[(1, 2, {"b"})] = b40
    assert b"c" not in c
    assert len(c) == 2


def test_multi_level_cache():
    l1: Dict[str, Any] = {}
    l2: Dict[str, Any] = {}
    cache = solara.cache.create("multi-level", l1, l2)
    with pytest.raises(KeyError):
        cache["key1"]
    assert l1 == {}
    assert l2 == {}
    # setting should fill all caches
    cache["key1"] = 1
    assert l1 == {"key1": 1}
    assert l2 == {"key1": 1}
    assert cache["key1"] == 1
    del l1["key1"]
    assert l1 == {}
    assert l2 == {"key1": 1}
    # reading should fill l1 as well
    assert cache["key1"] == 1
    assert l1 == {"key1": 1}
    assert l2 == {"key1": 1}

    cache2 = solara.cache.create("memory,disk")
    assert type(cache) is type(cache2)


def test_memoize_hook():
    result_values = []

    @solara.component
    def Test():
        count, set_count = solara.use_state(0)

        @solara.cache.memoize
        def f(x: int) -> int:
            return x**2

        result = f.use_thread(10)
        result_values.append(result)
        if result.state == solara.ResultState.FINISHED:
            return solara.Button(str(count), on_click=lambda: set_count(count + 1))
        else:
            return solara.Text("running")

    box, rc = solara.render(Test(), handle_error=False)
    rc.find(v.Btn, children=["0"]).wait_for(timeout=10)
    result_values.clear()
    click(rc.find(v.Btn).widget)
    rc.find(v.Btn, children=["1"]).wait_for(timeout=10)
    assert len(result_values) == 1
    # we should directly get the result from the cache, so we don't go into running state
    assert result_values[0].state == solara.ResultState.FINISHED
    assert result_values[0].value == 100


def test_memoize_hook_no_None_after_hit():
    has_been_none = False

    selected = solara.Reactive("1")

    @solara.memoize
    def something(i):
        return i

    @solara.component
    def Test():
        result = something.use_thread(selected.value)

        if result.state == solara.ResultState.FINISHED:
            if result.value is None:
                # this should not happen
                nonlocal has_been_none
                has_been_none = True

            solara.Text(str(result.value))

    box, rc = solara.render(Test(), handle_error=False)
    rc.find(v.Html, children=["1"]).wait_for(timeout=2)

    assert not has_been_none
    selected.set("2")
    rc.find(v.Html, children=["2"]).wait_for(timeout=2)
    assert not has_been_none

    selected.set("1")
    rc.find(v.Html, children=["1"]).wait_for(timeout=2)
    assert not has_been_none

    selected.set("3")
    rc.find(v.Html, children=["3"]).wait_for(timeout=2)
    assert not has_been_none
