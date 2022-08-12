import logging
import os
import pathlib
import sys

import requests

logger = logging.getLogger("Solara.cdn")

cdn = "https://cdn.jsdelivr.net/npm/"

default_cache_dir = pathlib.Path(sys.prefix + "/share/solara/cdn/")

try:
    os.makedirs(default_cache_dir, exist_ok=True)
    open(default_cache_dir / "_test_write_permission", "w").close()
except:  # noqa
    logger.exception(
        "Could not write to cache directory: %s, please configure the SOLARA_CDN_CACHE_PATH env var to point to a writable directory", default_cache_dir
    )
    sys.exit(1)

cdn_url_path = "_solara/cdn"


def put_in_cache(base_cache_dir: pathlib.Path, path, data: bytes):
    cache_path = base_cache_dir / path
    pathlib.Path(cache_path.parent).mkdir(parents=True, exist_ok=True)
    try:
        logger.info("Writing cache file: %s", cache_path)
        cache_path.write_bytes(data)
        logger.info("Wrote cache file: %s", cache_path)
    except:  # noqa
        logger.exception("Failed writing cache file: %s", cache_path)
        raise


def get_from_cache(base_cache_dir: pathlib.Path, path):
    cache_path = base_cache_dir / path
    try:
        logger.info("Opening cache file: %s", cache_path)
        return cache_path.read_bytes()
    except FileNotFoundError:
        pass


def get_cdn_url(path):
    return cdn + path


def get_data(base_cache_dir: pathlib.Path, path):
    parts = path.split("/")
    store_path = path if len(parts) != 1 else pathlib.Path(path) / "__main"

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
