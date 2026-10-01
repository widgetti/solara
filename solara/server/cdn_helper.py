import logging
import os
import pathlib
import secrets
import shutil
import time

import requests
from solara.server.utils import path_is_child_of

import solara.settings

logger = logging.getLogger("Solara.cdn")

cdn_url_path = "_solara/cdn"


def fetch_from_cdn(url) -> bytes:
    # retry: a single failed attempt (the CDN rate-limiting CI runners, a network blip) used to
    # become a 500 for the browser, permanently breaking the widget for that page load, since
    # only a success is cached
    last_status = None
    for attempt in range(4):
        if attempt:
            time.sleep(2 ** (attempt - 1))  # 1, 2, 4 seconds
        try:
            response = requests.get(url, timeout=10)
        except requests.RequestException as e:
            logger.warning("Could not load URL: %r (%s)", url, e)
            continue
        if response.ok:
            return response.content
        last_status = response.status_code
        logger.warning("Could not load URL: %r (status %s)", url, last_status)
        if 400 <= last_status < 500 and last_status != 429:
            break  # a permanent client error will not get better by retrying
    raise Exception(f"Could not load URL: {url} (last status: {last_status})")


def put_in_cache(base_cache_dir: pathlib.Path, path, data: bytes):
    cache_path = base_cache_dir / path
    if not path_is_child_of(cache_path, base_cache_dir):
        raise PermissionError("Trying to write outside of cache directory")

    pathlib.Path(cache_path.parent).mkdir(parents=True, exist_ok=True)
    try:
        logger.info("Writing cache file: %s", cache_path)
        # The server sends the cached file as soon as it exists, while concurrent requests
        # for an uncached file each fetch and write it. Writing in place let a request send
        # a half-written file, or one that another write truncated, which broke the page
        # (e.g. "requirejs is not defined"). Write a temporary file and rename it, so the
        # file is complete whenever it exists. The "x" mode creates the temporary file and
        # fails if anything (e.g. a symlink) has its random name; unlike tempfile.mkstemp
        # (mode 0600), it gives the file the usual permissions, which other users (a shared
        # environment, a static build served by another user) need to read it.
        tmp = cache_path.parent / f".{secrets.token_hex(8)}.tmp"
        try:
            with open(tmp, "xb") as f:
                f.write(data)
            try:
                os.replace(tmp, cache_path)
            except PermissionError:
                # Windows cannot replace a file that is open, e.g. by a request sending it;
                # that file was written the same way, so it is complete
                if not cache_path.exists():
                    raise
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
    except FileNotFoundError:
        logger.info("Failed writing cache file: %s", cache_path)


def get_from_cache(base_cache_dir: pathlib.Path, path):
    cache_path = pathlib.Path(base_cache_dir / path)
    # Make sure cache_path is a subdirectory of base_cache_dir
    # so we don't accidentally read files from the parent directory
    # which is a security risk.
    if not path_is_child_of(cache_path, base_cache_dir):
        logger.warning("Trying to read from outside of cache directory: %s is not a subdir of %s", cache_path, base_cache_dir)
        raise PermissionError("Trying to read from outside of cache directory")

    try:
        logger.info("Opening cache file: %s", cache_path)
        return cache_path.read_bytes()
    except FileNotFoundError:
        pass


def get_cdn_url(path):
    path = str(path)  # on windows, the path can contain a \
    return str(solara.settings.assets.cdn) + str(path).replace("\\", "/")


def get_data(base_cache_dir: pathlib.Path, path):
    parts = path.replace("\\", "/").split("/")
    store_path = path if len(parts) != 1 else pathlib.Path(path) / "__main.js"

    content = get_from_cache(base_cache_dir, store_path)
    if content:
        return content

    data = fetch_from_cdn(get_cdn_url(path))
    put_in_cache(base_cache_dir, store_path, data)
    return data


def get_path(base_cache_dir: pathlib.Path, path) -> pathlib.Path:
    parts = path.replace("\\", "/").split("/")
    store_path = path if len(parts) != 1 else pathlib.Path(path) / "__main.js"
    cache_path = base_cache_dir / store_path

    if not path_is_child_of(cache_path, base_cache_dir):
        raise PermissionError("Trying to read from outside of cache directory")

    if cache_path.exists():
        # before d7eba856f100d5c3c64f4eec22c62390f084cb40 on windows, we could
        # accidentally write to the cache directory, so we need to check if we still
        # have an old directory layout, and remove that first.
        if cache_path.is_dir():
            shutil.rmtree(cache_path)
        else:
            return cache_path
    data = fetch_from_cdn(get_cdn_url(path))
    put_in_cache(base_cache_dir, store_path, data)
    assert cache_path.exists(), f"Could not write to {cache_path}"
    return cache_path
