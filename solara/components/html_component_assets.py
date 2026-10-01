"""Content-addressed assets extracted from native HTML component files.

Only content explicitly registered by a component can be retrieved. The registry is
populated when application modules are imported in each server worker.
"""

from __future__ import annotations

import hashlib
import re
import threading

_ASSET_NAME = re.compile(r"^[0-9a-f]{64}\.(css|js)$")
_assets: dict[str, str] = {}
_lock = threading.Lock()


def register_component_asset(content: str, kind: str) -> str:
    """Register an extracted CSS or JS section and return its URL-safe filename."""
    if kind not in ("css", "js"):
        raise ValueError("HTML component asset kind must be 'css' or 'js'")
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    name = f"{digest}.{kind}"
    with _lock:
        _assets[name] = content
    return name


def get_component_asset(name: str) -> tuple[str, str] | None:
    """Return registered content and MIME type; unknown names never read files."""
    match = _ASSET_NAME.fullmatch(name)
    if match is None:
        return None
    with _lock:
        content = _assets.get(name)
    if content is None:
        return None
    media_type = "text/css" if match.group(1) == "css" else "text/javascript"
    return content, media_type
