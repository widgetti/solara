import logging
import pathlib
import shutil

import requests

import solara.settings

logger = logging.getLogger("Solara.cdn")

cdn_url_path = "_solara/cdn"


def put_in_cache(base_cache_dir: pathlib.Path, path, data: bytes):
    cache_path = base_cache_dir / path
    pathlib.Path(cache_path.parent).mkdir(parents=True, exist_ok=True)
    try:
        logger.info("Writing cache file: %s", cache_path)
        cache_path.write_bytes(data)
    except FileNotFoundError:
        logger.info("Failed writing cache file: %s", cache_path)


def get_from_cache(base_cache_dir: pathlib.Path, path):
    cache_path = base_cache_dir / path
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

    url = get_cdn_url(path)
    response = requests.get(url)
    if response.ok:
        put_in_cache(base_cache_dir, store_path, response.content)
        return response.content
    else:
        logger.warning("Could not load URL: %r", url)
        raise Exception(f"Could not load URL: {url}")


def get_path(base_cache_dir: pathlib.Path, path) -> pathlib.Path:
    parts = path.replace("\\", "/").split("/")
    store_path = path if len(parts) != 1 else pathlib.Path(path) / "__main.js"
    cache_path = base_cache_dir / store_path

    if cache_path.exists():
        # before d7eba856f100d5c3c64f4eec22c62390f084cb40 on windows, we could
        # accidentally write to the cache directory, so we need to check if we still
        # have an old directory layout, and remove that first.
        if cache_path.is_dir():
            shutil.rmtree(cache_path)
        else:
            return cache_path
    url = get_cdn_url(path)
    response = requests.get(url)
    if response.ok:
        put_in_cache(base_cache_dir, store_path, response.content)
        assert cache_path.exists(), f"Could not write to {cache_path}"
        return cache_path
    else:
        logger.warning("Could not load URL: %r", url)
        raise Exception(f"Could not load URL: {url}")
