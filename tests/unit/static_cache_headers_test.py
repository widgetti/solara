import hashlib
import json
import os
import re
from pathlib import Path
from typing import List

import pytest
from starlette.applications import Starlette
from starlette.routing import Mount
from starlette.testclient import TestClient

import solara.server.app
import solara.server.settings
import solara.server.starlette
from solara.server import server
from solara.server.app import AppScript
from solara.server.starlette import StaticAssets, StaticFilesOptionalAuth, StaticNbFiles, StaticPublic, immutable_cache_control

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
