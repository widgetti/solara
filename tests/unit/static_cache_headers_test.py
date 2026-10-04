import gzip
import hashlib
import json
import os
import re
from pathlib import Path
from typing import List

import pytest
import starlette.middleware.gzip
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.responses import PlainTextResponse, Response
from starlette.routing import Mount, Route
from starlette.testclient import TestClient

import solara.server.app
import solara.server.settings
import solara.server.starlette
from solara.server import compress, server
from solara.server.app import AppScript
from solara.server.starlette import (
    SolaraGZipMiddleware,
    StaticAssets,
    StaticCdn,
    StaticFilesOptionalAuth,
    StaticNbFiles,
    StaticPublic,
    immutable_cache_control,
)

CONTENT = b"console.log('hi')"
DIGEST = hashlib.md5(CONTENT).hexdigest()
IMMUTABLE = "public, max-age=31536000, immutable"


@pytest.fixture(autouse=True)
def production(monkeypatch):
    monkeypatch.setattr(solara.server.settings.main, "mode", "production")
    monkeypatch.setattr(server, "_content_hash_cache", {})
    monkeypatch.setattr(server, "_nbextension_hash_cache", {})


@pytest.fixture
def development(monkeypatch):
    monkeypatch.setattr(solara.server.settings.main, "mode", "development")


@pytest.fixture
def static_dir(tmp_path: Path) -> Path:
    static = tmp_path / "static"
    static.mkdir()
    (static / "main.js").write_bytes(CONTENT)
    return static


def client_for(app) -> TestClient:
    return TestClient(Starlette(routes=[Mount("/static", app=app)]))


def cache_control(client: TestClient, url: str):
    return client.get(url).headers.get("cache-control")


@pytest.mark.parametrize("mode", ["production", "development"])
@pytest.mark.parametrize("version", [DIGEST, DIGEST[:12]], ids=["full-md5", "short-md5"])
def test_current_content_hash_is_immutable(static_dir: Path, version: str, mode: str, monkeypatch):
    monkeypatch.setattr(solara.server.settings.main, "mode", mode)
    client = client_for(StaticFilesOptionalAuth(directory=static_dir))

    response = client.get(f"/static/main.js?v={version}")

    assert response.status_code == 200
    assert response.headers["cache-control"] == IMMUTABLE


@pytest.mark.parametrize("query", ["", "?x=1"], ids=["no-version", "other-query"])
def test_unversioned_urls_get_no_cache_header(static_dir: Path, query: str):
    client = client_for(StaticFilesOptionalAuth(directory=static_dir))

    assert cache_control(client, f"/static/main.js{query}") is None


def test_stale_version_is_not_stored(static_dir: Path):
    # e.g. a rolling deploy: the page came from a server with the other version of the file
    client = client_for(StaticFilesOptionalAuth(directory=static_dir))

    assert cache_control(client, "/static/main.js?v=0123456789ab") == "no-store"


def test_revalidation_keeps_the_header(static_dir: Path):
    client = client_for(StaticFilesOptionalAuth(directory=static_dir))
    etag = client.get(f"/static/main.js?v={DIGEST}").headers["etag"]

    response = client.get(f"/static/main.js?v={DIGEST}", headers={"if-none-match": etag})

    assert response.status_code == 304
    assert response.headers["cache-control"] == IMMUTABLE


def test_production_hashes_each_file_once(static_dir: Path):
    # production files do not change on disk while the server runs
    client = client_for(StaticFilesOptionalAuth(directory=static_dir))
    assert cache_control(client, f"/static/main.js?v={DIGEST}") == IMMUTABLE

    (static_dir / "main.js").write_bytes(b"console.log('changed')")

    assert server.file_content_hash(static_dir / "main.js") == DIGEST


@pytest.mark.usefixtures("development")
def test_development_checks_the_file_on_every_request(static_dir: Path):
    client = client_for(StaticFilesOptionalAuth(directory=static_dir))
    path = static_dir / "main.js"
    assert cache_control(client, f"/static/main.js?v={DIGEST}") == IMMUTABLE
    stat = path.stat()

    # same size and modification time: only the content tells
    changed = b"console.log('ho')"
    path.write_bytes(changed)
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns))

    assert cache_control(client, f"/static/main.js?v={DIGEST}") == "no-store"
    assert cache_control(client, f"/static/main.js?v={hashlib.md5(changed).hexdigest()}") == IMMUTABLE


def test_public_url_versioned_by_versioned_url(static_dir: Path, monkeypatch):
    monkeypatch.setattr(StaticPublic, "get_directories", lambda self, directory=None, packages=None: [static_dir])
    monkeypatch.setattr(server, "public_directories", lambda: [static_dir])
    client = client_for(StaticPublic())

    url = server.versioned_url("/static/public/main.js").replace("/static/public", "/static")

    assert cache_control(client, url) == IMMUTABLE


def test_large_files_are_not_hashed(static_dir: Path, monkeypatch):
    monkeypatch.setattr(solara.server.starlette, "MAX_VERSIONED_FILE_SIZE", len(CONTENT) - 1)
    client = client_for(StaticFilesOptionalAuth(directory=static_dir))

    assert cache_control(client, f"/static/main.js?v={DIGEST}") == "no-store"


def test_private_deployments_keep_files_out_of_shared_caches(monkeypatch):
    monkeypatch.setattr(solara.server.settings.oauth, "private", True)

    assert immutable_cache_control() == "private, max-age=31536000, immutable"


def write_extension(directory: Path, folder: str, files: List[str]) -> None:
    (directory / folder).mkdir(parents=True, exist_ok=True)
    for name in files:
        (directory / folder / name).write_text(f"// {folder}/{name}")


def nbextension_client(monkeypatch, directories: List[Path], names: List[str]) -> TestClient:
    monkeypatch.setattr(server, "nbextensions_directories", directories)
    monkeypatch.setattr(server, "get_nbextension_names", lambda: names)
    return client_for(StaticNbFiles())


def test_nbextension_files_are_immutable_with_their_extension_hash(tmp_path: Path, monkeypatch):
    write_extension(tmp_path, "ext", ["extension.js", "nodeps.js"])
    write_extension(tmp_path, "other", ["extension.js"])
    client = nbextension_client(monkeypatch, [tmp_path], ["ext/extension", "other/extension"])
    _, hashes = server.get_nbextensions()

    assert cache_control(client, f"/static/ext/nodeps.js?{hashes['ext/extension']}") == IMMUTABLE
    assert cache_control(client, f"/static/ext/nodeps.js?{hashes['other/extension']}") == "no-store"
    assert cache_control(client, "/static/ext/nodeps.js") is None


def test_nbextension_file_from_another_directory_is_not_covered(tmp_path: Path, monkeypatch):
    # ext/extra.js is not in the folder that was hashed: it is served from the second directory
    first, second = tmp_path / "first", tmp_path / "second"
    write_extension(first, "ext", ["extension.js"])
    write_extension(second, "ext", ["extension.js", "extra.js"])
    client = nbextension_client(monkeypatch, [first, second], ["ext/extension"])
    _, hashes = server.get_nbextensions()

    assert cache_control(client, f"/static/ext/extension.js?{hashes['ext/extension']}") == IMMUTABLE
    assert cache_control(client, f"/static/ext/extra.js?{hashes['ext/extension']}") == "no-store"


@pytest.mark.usefixtures("development")
def test_development_follows_an_edit_in_a_symlinked_nbextension(tmp_path: Path, monkeypatch):
    # jupyter nbextension install --symlink: the extension folder links to the source tree
    source, nbextensions = tmp_path / "source", tmp_path / "nbextensions"
    write_extension(source, "ext", ["extension.js", "nodeps.js"])
    nbextensions.mkdir()
    (nbextensions / "ext").symlink_to(source / "ext")
    client = nbextension_client(monkeypatch, [nbextensions], ["ext/extension"])
    before = server.get_nbextensions()[1]["ext/extension"]
    assert cache_control(client, f"/static/ext/nodeps.js?{before}") == IMMUTABLE

    (source / "ext" / "nodeps.js").write_text("// edited")
    after = server.get_nbextensions()[1]["ext/extension"]

    assert after != before
    assert cache_control(client, f"/static/ext/nodeps.js?{before}") == "no-store"
    assert cache_control(client, f"/static/ext/nodeps.js?{after}") == IMMUTABLE


def test_page_fetches_the_theme_css_from_immutable_urls(no_kernel_context, tmp_path: Path, monkeypatch):
    app_file = tmp_path / "app.py"
    app_file.write_text("import solara\n\n\n@solara.component\ndef Page():\n    solara.Text('hi')\n")
    app_script = AppScript(str(app_file))
    monkeypatch.setitem(solara.server.app.apps, "__default__", app_script)
    try:
        html = server.read_root("/")
    finally:
        app_script.close()
    assert html is not None
    match = re.search(r"const themeCssUrls = (\{.*?\});", html)
    assert match is not None
    urls = json.loads(match.group(1))
    client = TestClient(Starlette(routes=[Mount("/static/assets", app=StaticAssets())]))

    assert set(urls) == {"light", "dark"}
    for url in urls.values():
        assert "?v=" in url
        assert cache_control(client, url) == IMMUTABLE


BIG = b"console.log('hello solara');\n" * 200
BIG_DIGEST = hashlib.md5(BIG).hexdigest()


@pytest.fixture(autouse=True)
def empty_compress_cache():
    compress.clear()
    yield
    compress.clear()


@pytest.fixture
def compress_calls(monkeypatch) -> List[str]:
    calls: List[str] = []
    original = compress._compress

    def counting(data: bytes, encoding: str) -> bytes:
        calls.append(encoding)
        return original(data, encoding)

    monkeypatch.setattr(compress, "_compress", counting)
    return calls


def gzip_client(app) -> TestClient:
    # with the middleware the server uses, so a response compressed twice would show
    return TestClient(Starlette(routes=[Mount("/static", app=app)], middleware=[Middleware(SolaraGZipMiddleware, minimum_size=1000)]))


@pytest.mark.parametrize("encoding", ["gzip", "br"])
def test_static_compressed_once(static_dir: Path, encoding: str, compress_calls: List[str]):
    if encoding == "br":
        pytest.importorskip("brotli")
    (static_dir / "big.js").write_bytes(BIG)
    client = gzip_client(StaticFilesOptionalAuth(directory=static_dir))
    url = f"/static/big.js?v={BIG_DIGEST}"

    for _ in range(2):
        response = client.get(url, headers={"accept-encoding": encoding})
        assert response.status_code == 200
        assert response.headers["content-encoding"] == encoding
        assert response.headers["vary"] == "Accept-Encoding"
        assert response.headers["cache-control"] == IMMUTABLE
        assert int(response.headers["content-length"]) < len(BIG)
        # the client removes one layer of compression: a second layer would show here
        assert response.content == BIG
    assert compress_calls == [encoding]

    # the body is not the file's bytes: a weak etag, which still revalidates
    etag = response.headers["etag"]
    assert etag.startswith('W/"')
    response = client.get(url, headers={"accept-encoding": encoding, "if-none-match": etag})
    assert response.status_code == 304
    assert response.headers["cache-control"] == IMMUTABLE


def test_static_prefers_brotli_when_accepted(static_dir: Path):
    pytest.importorskip("brotli")
    (static_dir / "big.js").write_bytes(BIG)
    client = gzip_client(StaticFilesOptionalAuth(directory=static_dir))

    assert client.get("/static/big.js", headers={"accept-encoding": "gzip, deflate, br"}).headers["content-encoding"] == "br"
    assert client.get("/static/big.js", headers={"accept-encoding": "gzip, br;q=0"}).headers["content-encoding"] == "gzip"


def test_static_gzip_without_brotli(static_dir: Path, compress_calls: List[str], monkeypatch):
    # brotli is opt-in (the solara-server[brotli] extra): without it, a client that accepts br gets gzip
    monkeypatch.setattr(compress, "brotli", None)
    (static_dir / "big.js").write_bytes(BIG)
    client = gzip_client(StaticFilesOptionalAuth(directory=static_dir))

    response = client.get("/static/big.js", headers={"accept-encoding": "gzip, deflate, br"})

    assert response.headers["content-encoding"] == "gzip"
    assert response.content == BIG
    assert compress_calls == ["gzip"]


def test_static_range_request_gets_identity(static_dir: Path, compress_calls: List[str]):
    (static_dir / "big.js").write_bytes(BIG)
    client = gzip_client(StaticFilesOptionalAuth(directory=static_dir))

    response = client.get("/static/big.js", headers={"accept-encoding": "gzip", "range": "bytes=0-9"})

    assert response.status_code == 206
    assert "content-encoding" not in response.headers
    assert response.content == BIG[:10]
    assert compress_calls == []


def test_static_not_compressed_without_http_gzip(static_dir: Path, compress_calls: List[str], monkeypatch):
    # SOLARA_SERVER_HTTP_GZIP=false: a proxy in front of the server compresses
    monkeypatch.setattr(solara.server.settings.server, "http_gzip", False)
    (static_dir / "big.js").write_bytes(BIG)
    client = client_for(StaticFilesOptionalAuth(directory=static_dir))

    response = client.get("/static/big.js", headers={"accept-encoding": "gzip, br"})

    assert response.status_code == 200
    assert "content-encoding" not in response.headers
    assert response.content == BIG
    assert compress_calls == []


def test_static_small_and_binary_files_are_not_compressed(static_dir: Path, compress_calls: List[str]):
    (static_dir / "big.png").write_bytes(BIG)
    # without the middleware: (depending on the starlette version) it may gzip a png, as it always did
    client = client_for(StaticFilesOptionalAuth(directory=static_dir))

    for name in ["main.js", "big.png"]:
        response = client.get(f"/static/{name}", headers={"accept-encoding": "gzip"})
        assert response.status_code == 200
        assert "content-encoding" not in response.headers
    assert compress_calls == []


def test_static_compression_follows_a_changed_file(static_dir: Path, compress_calls: List[str]):
    path = static_dir / "big.js"
    path.write_bytes(BIG)
    client = client_for(StaticFilesOptionalAuth(directory=static_dir))
    assert client.get("/static/big.js", headers={"accept-encoding": "gzip"}).content == BIG

    changed = BIG + b"// changed\n"
    path.write_bytes(changed)
    stat = path.stat()
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000))

    assert client.get("/static/big.js", headers={"accept-encoding": "gzip"}).content == changed
    assert compress_calls == ["gzip", "gzip"]


def test_cdn_proxy_compressed_and_immutable(tmp_path: Path, monkeypatch):
    cache_dir = tmp_path / "cdn"
    path = cache_dir / "pkg@1.2.3" / "dist" / "big.js"
    path.parent.mkdir(parents=True)
    path.write_bytes(BIG)
    monkeypatch.setattr(solara.server.settings.assets, "proxy_cache_dir", cache_dir)
    client = gzip_client(StaticCdn(directory=cache_dir))

    response = client.get("/static/pkg@1.2.3/dist/big.js", headers={"accept-encoding": "gzip"})

    assert response.status_code == 200
    assert response.headers["content-encoding"] == "gzip"
    assert response.headers["cache-control"] == IMMUTABLE
    assert response.content == BIG


@pytest.mark.parametrize(
    "path, sep, expected",
    [
        ("@widgetti/solara-vuetify3-app@5.2.0/dist/main8.css", "/", True),
        # Windows: StaticFiles.get_path returns an OS path
        ("@widgetti\\solara-vuetify3-app@5.2.0\\dist\\main8.css", "\\", True),
        ("requirejs@2.3.6\\require.js", "\\", True),
        ("pkg@^1\\index.js", "\\", False),
        ("pkg@1.2\\index.js", "\\", False),
    ],
)
def test_cdn_proxy_exact_version_os_paths(path: str, sep: str, expected: bool):
    assert StaticCdn._pins_exact_version(path, sep) is expected


def test_gzip_middleware_sends_encoded_responses_as_they_are():
    # the static mounts compress (once) themselves; the middleware compresses the rest
    def text(request):
        if request.url.path == "/encoded":
            return Response(gzip.compress(BIG), headers={"content-encoding": "gzip"})
        return PlainTextResponse(BIG.decode())

    app = Starlette(routes=[Route("/{path:path}", endpoint=text)], middleware=[Middleware(SolaraGZipMiddleware, minimum_size=1000)])
    client = TestClient(app)

    response = client.get("/encoded", headers={"accept-encoding": "gzip"})
    assert response.headers["content-encoding"] == "gzip"
    # the client removes one layer of compression: a second layer would show here
    assert response.content == BIG
    for path in ["/", "/static/big.bin"]:
        response = client.get(path, headers={"accept-encoding": "gzip"})
        assert response.headers["content-encoding"] == "gzip"
        assert response.content == BIG


@pytest.mark.parametrize("name", ["data.geojson", "big.js"])
def test_static_files_compress_skips_are_gzipped_as_before(static_dir: Path, compress_calls: List[str], monkeypatch, name: str):
    # an unlisted suffix, or a file over MAX_SIZE: the GZip middleware compresses it (streaming), as before
    monkeypatch.setattr(compress, "MAX_SIZE", len(BIG) - 1)
    (static_dir / name).write_bytes(BIG)
    client = gzip_client(StaticFilesOptionalAuth(directory=static_dir))

    response = client.get(f"/static/{name}", headers={"accept-encoding": "gzip, br"})

    assert response.status_code == 200
    assert response.headers["content-encoding"] == "gzip"
    assert response.content == BIG
    assert compress_calls == []


def test_static_identity_response_varies_as_before(static_dir: Path):
    # a shared cache must not serve the identity response to clients that accept gzip
    (static_dir / "big.js").write_bytes(BIG)
    client = gzip_client(StaticFilesOptionalAuth(directory=static_dir))

    response = client.get("/static/big.js", headers={"accept-encoding": "identity"})

    assert "content-encoding" not in response.headers
    assert response.content == BIG
    if hasattr(starlette.middleware.gzip, "IdentityResponder"):
        # newer starlette versions add it for every response the middleware could have compressed
        assert response.headers["vary"] == "Accept-Encoding"


def test_compress_cache_counts_a_key_stored_twice_once(monkeypatch):
    # after an eviction, two requests for the same file can both compress it and store it
    monkeypatch.setattr(compress, "CACHE_SIZE", 100)
    key = ("/a.js", 1, 2, "gzip")
    compress._store(key, b"x" * 40)
    compress._store(key, b"y" * 40)
    assert compress._cache_bytes == sum(len(data) for data in compress._cache.values()) == 40
    # a drift in the count would evict entries that fit
    compress._store(("/b.js", 1, 2, "gzip"), b"z" * 40)
    assert len(compress._cache) == 2


def test_compress_keeps_the_key_lock_of_another_request(static_dir: Path, monkeypatch):
    # a request that ends must not drop the lock a later request made for the same key
    (static_dir / "big.js").write_bytes(BIG)
    path = str(static_dir / "big.js")
    stat_result = os.stat(path)
    key = (path, stat_result.st_mtime_ns, stat_result.st_size, "gzip")
    other_lock = compress.threading.Lock()
    original = compress._compress

    def compress_and_replace_lock(data: bytes, encoding: str) -> bytes:
        compress._key_locks[key] = other_lock
        return original(data, encoding)

    monkeypatch.setattr(compress, "_compress", compress_and_replace_lock)
    assert gzip.decompress(compress.compressed(path, stat_result, "gzip")) == BIG
    assert compress._key_locks.pop(key) is other_lock
