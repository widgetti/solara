import hashlib
import os
from pathlib import Path

from solara.server.cdn_helper import get_cdn_url, get_data, get_from_cache, put_in_cache, get_path


def norm(path):
    # this is what starlette does
    return os.path.normpath(os.path.join(*path.split("/")))


path1 = norm("vue-grid-layout@1.0.2/dist/vue-grid-layout.min.js")
hash1 = norm("4bd3c14b1fa124bd9fe4cb5f8a7cbc54")
path2 = norm("@widgetti/vue-grid-layout@2.3.13-alpha.2/dist/vue-grid-layout.umd.js")
hash2 = norm("91c2f41b719978849602e14e17abfb20")


def test_cache(tmp_path_factory):
    base_cache_dir = tmp_path_factory.mktemp("cdn")

    put_in_cache(base_cache_dir, path1, b"test1")
    assert (base_cache_dir / path1).is_file()
    data = get_from_cache(base_cache_dir, path1)
    assert data == b"test1"

    put_in_cache(base_cache_dir, path2, b"test2")
    assert (base_cache_dir / path2).is_file()
    data = get_from_cache(base_cache_dir, path2)
    assert data == b"test2"


def test_cdn_url():
    assert get_cdn_url(path1) == f"https://cdn.jsdelivr.net/npm/{path1}".replace("\\", "/")
    assert get_cdn_url(path2) == f"https://cdn.jsdelivr.net/npm/{path2}".replace("\\", "/")


def test_get_path(tmpdir):
    full_path = get_path(Path(tmpdir), path1)
    assert str(full_path).endswith("vue-grid-layout.min.js")


def test_get_data(tmp_path_factory):
    base_cache_dir = tmp_path_factory.mktemp("cdn")

    # test path1
    data = get_data(base_cache_dir, path1)
    assert hashlib.md5(data).hexdigest() == hash1
    assert (base_cache_dir / path1).is_file()

    assert hashlib.md5((base_cache_dir / path1).read_bytes()).hexdigest() == hash1

    (base_cache_dir / path1).write_bytes(b"test_cached_1")

    data = get_data(base_cache_dir, path1)
    assert data == b"test_cached_1"

    # test path2
    data = get_data(base_cache_dir, path2)
    assert hashlib.md5(data).hexdigest() == hash2
    assert (base_cache_dir / path2).is_file()

    assert hashlib.md5((base_cache_dir / path2).read_bytes()).hexdigest() == hash2

    (base_cache_dir / path2).write_bytes(b"test_cached_2")

    data = get_data(base_cache_dir, path2)
    assert data == b"test_cached_2"


def test_redirect(tmp_path_factory):
    base_cache_dir = tmp_path_factory.mktemp("cdn")

    data = get_data(base_cache_dir, "codemirror@5.65.3")

    assert len(data) > 0

    data = get_data(base_cache_dir, "codemirror@5.65.3/lib/codemirror.js")
    assert len(data) > 0


def test_binary(tmp_path_factory):
    base_cache_dir = tmp_path_factory.mktemp("cdn")

    lib = "@widgetti/solara-vuetify-app@0.0.1-alpha.1/dist/037d830416495def72b7881024c14b7b.woff2"
    data = get_data(base_cache_dir, lib)
    assert len(data) == 15436

    assert len((base_cache_dir / lib).read_bytes()) == 15436
