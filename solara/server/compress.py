"""Compress static files once per process, and keep the result in memory.

Compressing on every request (what GZipMiddleware does) costs ~350 ms of server
CPU per cold page load with the Vue 3 bundles. Static files do not change for a
given (path, mtime, size), so we compress each file once, with brotli when the
client accepts it and the brotli package is installed, else with gzip.
"""

import gzip
import os
import threading
from collections import OrderedDict
from pathlib import Path
from typing import Dict, Optional, Tuple

import anyio.to_thread
from starlette.datastructures import Headers
from starlette.responses import FileResponse, Response
from starlette.types import Scope

from . import server, settings

try:
    import brotli
except ImportError:  # optional, opt-in with the solara[brotli] or solara-server[brotli] extra
    brotli = None  # type: ignore

COMPRESSIBLE_SUFFIXES = {
    ".js",
    ".mjs",
    ".cjs",
    ".css",
    ".json",
    ".map",
    ".svg",
    ".html",
    ".htm",
    ".txt",
    ".xml",
    ".csv",
    ".tsv",
    ".md",
    ".py",
    ".ipynb",
    ".vue",
    ".wasm",
    ".ttf",
    ".otf",
    ".eot",
    ".ico",
}
MIN_SIZE = 1024
# larger than every bundle, chunk and source map; a larger file is read into memory per request, so
# it streams through the GZip middleware instead
MAX_SIZE = 8 * 1024 * 1024
CACHE_SIZE = 64 * 1024 * 1024
# 9 as GZipMiddleware used before, so a client without brotli gets no more bytes than before;
# we compress each file only once, so the extra CPU does not matter
GZIP_LEVEL = 9
BROTLI_QUALITY = 5

Key = Tuple[str, int, int, str, str]

_lock = threading.Lock()
_cache: "OrderedDict[Key, bytes]" = OrderedDict()
_cache_bytes = 0
_key_locks: Dict[Key, threading.Lock] = {}


def clear():
    global _cache_bytes
    with _lock:
        _cache.clear()
        _cache_bytes = 0


def choose_encoding(accept_encoding: str) -> Optional[str]:
    """Return "br", "gzip" or None for an Accept-Encoding request header.

    The highest q value wins, and brotli wins a tie with gzip.
    """
    weights: Dict[str, float] = {}
    for part in accept_encoding.split(","):
        name, _, params = part.partition(";")
        name = name.strip().lower()
        q = 1.0
        for param in params.split(";"):
            key, _, value = param.partition("=")
            if key.strip().lower() == "q":
                try:
                    q = float(value)
                except ValueError:
                    q = 0.0
        if name:
            weights[name] = q
    # max keeps the first of equal weights
    best = max(["br", "gzip"] if brotli is not None else ["gzip"], key=lambda name: weights.get(name, 0.0))
    if weights.get(best, 0.0) <= 0 or weights.get("identity", 0.0) > weights[best]:
        return None
    return best


def _compress(data: bytes, encoding: str) -> bytes:
    if encoding == "br":
        assert brotli is not None
        return brotli.compress(data, quality=BROTLI_QUALITY)
    # mtime=0 gives the same bytes for the same file
    return gzip.compress(data, compresslevel=GZIP_LEVEL, mtime=0)


def _store(key: Key, data: bytes) -> None:
    global _cache_bytes
    if len(data) > CACHE_SIZE:
        return
    # two threads can store the same key (after an eviction): count each entry once
    old = _cache.pop(key, None)
    if old is not None:
        _cache_bytes -= len(old)
    _cache[key] = data
    _cache_bytes += len(data)
    while _cache_bytes > CACHE_SIZE:
        _, evicted = _cache.popitem(last=False)
        _cache_bytes -= len(evicted)


def compressed(path: str, stat_result: os.stat_result, encoding: str) -> bytes:
    """Return the compressed content of the file, from the cache when possible.

    A lock per key makes concurrent requests for the same file compress it once.
    In development a file can change without a new size or mtime, so the key also
    holds the hash of the current content there (as server.file_content_hash does).
    """
    digest = "" if settings.main.mode == "production" else server.file_content_hash(Path(path))
    key: Key = (path, stat_result.st_mtime_ns, stat_result.st_size, encoding, digest)
    with _lock:
        data = _cache.get(key)
        if data is not None:
            _cache.move_to_end(key)
            return data
        key_lock = _key_locks.setdefault(key, threading.Lock())
    with key_lock:
        with _lock:
            data = _cache.get(key)
            if data is not None:
                _cache.move_to_end(key)
                return data
        try:
            with open(path, "rb") as f:
                raw = f.read()
                now = os.fstat(f.fileno())
            data = _compress(raw, encoding)
            with _lock:
                # the file changed after the stat: serve it, but do not cache it under the old key
                if (now.st_mtime_ns, now.st_size) == (stat_result.st_mtime_ns, stat_result.st_size):
                    _store(key, data)
        finally:
            with _lock:
                # after an eviction a later request may have made a new lock for this key: keep that one
                if _key_locks.get(key) is key_lock:
                    del _key_locks[key]
    return data


def _should_compress(response: Response, scope: Scope) -> Optional[str]:
    if not settings.server.http_gzip:  # e.g. a fronting proxy does the compressing
        return None
    if not isinstance(response, FileResponse) or response.status_code != 200 or scope["method"] != "GET":
        return None
    stat_result = response.stat_result
    if stat_result is None or not (MIN_SIZE <= stat_result.st_size <= MAX_SIZE):
        return None
    if os.path.splitext(str(response.path))[1].lower() not in COMPRESSIBLE_SUFFIXES:
        return None
    request_headers = Headers(scope=scope)
    if "range" in request_headers:  # FileResponse serves the byte range of the identity body
        return None
    return choose_encoding(request_headers.get("accept-encoding", ""))


async def compress_file_response(response: Response, scope: Scope) -> Response:
    """Replace a 200 FileResponse for a GET by a compressed Response when the client accepts it.

    Other responses (304, Range requests, small or binary files) pass through.
    """
    encoding = _should_compress(response, scope)
    if encoding is None:
        return response
    assert isinstance(response, FileResponse) and response.stat_result is not None
    data = await anyio.to_thread.run_sync(compressed, str(response.path), response.stat_result, encoding)
    headers = {k: v for k, v in response.headers.items() if k not in ("content-length", "accept-ranges")}
    headers["content-encoding"] = encoding
    vary = headers.get("vary")
    headers["vary"] = f"{vary}, Accept-Encoding" if vary else "Accept-Encoding"
    etag = headers.get("etag")
    # the compressed body is not byte-identical to the file: a weak ETag (like nginx does).
    # StaticFiles.is_not_modified ignores the W/ prefix, so revalidation still gives a 304.
    if etag and not etag.startswith("W/"):
        headers["etag"] = "W/" + etag
    return Response(content=data, status_code=response.status_code, headers=headers, background=response.background)
