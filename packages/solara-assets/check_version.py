"""Fail when a built wheel differs from the wheel on PyPI with the same version.

The release job skips versions that are already on PyPI. Without this check, a
change to the assets without a version bump would never reach users.

Usage: python check_version.py dist/solara_assets2-1.0.0-py3-none-any.whl
"""

import json
import sys
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Dict, List, Optional


def wheel_files(path: Path) -> Dict[str, str]:
    "Maps each file in the wheel to its hash, without RECORD, which lists these hashes."
    with zipfile.ZipFile(path) as wheel:
        record_name = next(name for name in wheel.namelist() if name.endswith(".dist-info/RECORD"))
        lines = wheel.read(record_name).decode("utf8").splitlines()
    rows = [line.split(",") for line in lines if line]
    return {row[0]: row[1] for row in rows if row[0] != record_name}


def differences(built: Dict[str, str], published: Dict[str, str]) -> List[str]:
    return sorted(name for name in set(built) | set(published) if built.get(name) != published.get(name))


def published_wheel_url(version: str) -> Optional[str]:
    try:
        with urllib.request.urlopen(f"https://pypi.org/pypi/solara-assets2/{version}/json") as response:
            urls = json.load(response)["urls"]
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise
    return next(url["url"] for url in urls if url["packagetype"] == "bdist_wheel")


def main(wheel: str) -> int:
    path = Path(wheel)
    version = path.name.split("-")[1]
    url = published_wheel_url(version)
    if url is None:
        print(f"solara-assets2 {version} is not on PyPI yet, the release will publish it")  # noqa
        return 0
    with TemporaryDirectory() as directory:
        published = Path(directory) / path.name
        urllib.request.urlretrieve(url, published)
        changed = differences(wheel_files(path), wheel_files(published))
    if changed:
        print(f"solara-assets2 {version} is already on PyPI with different content, see packages/solara-assets/RELEASE.md to bump the version.")  # noqa
        print("\n".join(changed[:50]))  # noqa
        return 1
    print(f"solara-assets2 {version} on PyPI has the same content, the release will skip it")  # noqa
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
