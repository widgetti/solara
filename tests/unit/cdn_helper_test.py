import hashlib
import os
import threading
from pathlib import Path

from pytest import TempPathFactory
import pytest

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


def test_put_in_cache_never_shows_a_partial_file(tmp_path: Path):
    # The server sends the cached file as soon as it exists, while concurrent requests for
    # an uncached file each fetch and write it: whenever the file exists, it must be complete.
    path = norm("pkg@1.0.0/dist/big.js")
    data = b"x" * (16 * 1024 * 1024)
    cache_path = tmp_path / path
    sizes = set()
    done = threading.Event()

    def watch():
        while not done.is_set():
            try:
                sizes.add(os.stat(cache_path).st_size)
            except FileNotFoundError:
                pass

    watcher = threading.Thread(target=watch)
    watcher.start()
    try:
        for _ in range(20):
            put_in_cache(tmp_path, path, data)
    finally:
        done.set()
        watcher.join()
    assert sizes <= {len(data)}


def test_put_in_cache_while_the_file_is_open(tmp_path: Path):
    # a request may be sending the file while another one writes it (on Windows an open
    # file cannot be replaced)
    path = norm("pkg@1.0.0/dist/small.js")
    put_in_cache(tmp_path, path, b"content")
    with open(tmp_path / path, "rb") as f:
        put_in_cache(tmp_path, path, b"content")
        assert f.read() == b"content"
    assert (tmp_path / path).read_bytes() == b"content"
    assert [p.name for p in (tmp_path / path).parent.iterdir()] == ["small.js"]


def test_put_in_cache_permissions(tmp_path: Path):
    # the same permissions as any file the server writes: other users may need to read it
    put_in_cache(tmp_path, "new.js", b"content")
    (tmp_path / "plain.js").write_bytes(b"content")
    assert os.stat(tmp_path / "new.js").st_mode == os.stat(tmp_path / "plain.js").st_mode


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


def test_get_data_secure(tmp_path_factory: TempPathFactory):
    # we should never be able to get data from the parent directory

    root_dir = tmp_path_factory.mktemp("root")
    base_cache_dir = root_dir / "cdn"
    base_cache_dir.mkdir()

    (root_dir / "secret").write_bytes(b"not allowed")

    project_dir = base_cache_dir / "project"
    project_dir.mkdir()

    (project_dir / "file").write_bytes(b"a")

    data = get_data(base_cache_dir, "project/file")
    assert data == b"a"
    with pytest.raises(PermissionError):
        get_data(base_cache_dir, "project/../../secret")

    # test that we cannot access sibling directories with similar prefixes
    sibling_dir = root_dir / "cdn_sibling"
    sibling_dir.mkdir()
    (sibling_dir / "secret").write_bytes(b"not allowed")
    with pytest.raises(PermissionError):
        get_data(base_cache_dir, "../cdn_sibling/secret")


def test_path_is_child_of_symlink(tmp_path: Path):
    # symlinks should be allowed, this is needed for editable installs
    from solara.server.utils import path_is_child_of

    allowed = tmp_path / "allowed"
    allowed.mkdir()

    actual = tmp_path / "actual_package"
    actual.mkdir()
    (actual / "file.py").write_text("content")

    # Create symlink inside allowed pointing outside
    symlink = allowed / "symlink"
    symlink.symlink_to("../actual_package")

    # The path accessed via allowed/symlink/file.py should be allowed
    test_path = allowed / "symlink" / "file.py"
    assert path_is_child_of(test_path, allowed)


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
