"""Serve component_vue templates from a precompiled ES module bundle.

The @component_vue decorator records every .vue file it is given. From that,
`write_bundle_entry` generates a vite/rollup entry (one export per template)
plus a manifest mapping each template's content hash to its export name.

With SOLARA_VUE_BUNDLES set (comma-separated manifest paths), component_vue
resolves templates through the manifests instead of shipping their source:
the widget uses Template(esm_module=..., esm_export=...) (requires ipyvue
with ES module support). A template whose current content hash is not in any
manifest is a hard error - a changed file means the bundle is stale.

Building the bundle (running vite) and defining the module
(ipyvue.define_module with a Path or url) remain the application's
responsibility; solara only generates text and checks it.
"""

import hashlib
import json
import logging
import os
import pathlib
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# every .vue file passed to @component_vue, in import order, with the
# decorated function's name (used as the export name)
_vue_files: Dict[Path, str] = {}

_manifests: Optional[Dict[str, Tuple[str, str]]] = None  # sha1 -> (module, export)
_manifest_names: Dict[str, List[str]] = {}  # basename -> manifest names, for errors
_loaded_bundles: List[str] = []  # manifest names, for errors


def _sha1(path: Path) -> str:
    return hashlib.sha1(path.read_bytes()).hexdigest()  # noqa: S324 - content id, not security


def record(vue_file: Path, component_name: str) -> None:
    vue_file = vue_file.resolve()
    if vue_file not in _vue_files:
        _vue_files[vue_file] = component_name


def _load_manifests() -> Dict[str, Tuple[str, str]]:
    global _manifests
    if _manifests is None:
        _manifests = {}
        for manifest_path in os.environ.get("SOLARA_VUE_BUNDLES", "").split(","):
            if not manifest_path.strip():
                continue
            manifest = json.loads(Path(manifest_path.strip()).read_text(encoding="utf8"))
            _loaded_bundles.append(manifest["name"])
            for file, entry in manifest["components"].items():
                _manifests[entry["sha1"]] = (manifest["name"], entry["export"])
                _manifest_names.setdefault(Path(file).name, []).append(manifest["name"])
    return _manifests


def enabled() -> bool:
    return bool(os.environ.get("SOLARA_VUE_BUNDLES"))


def lookup(vue_file: Path) -> Tuple[str, str]:
    """Resolve a template to (esm_module, esm_export), or raise if the bundle
    does not contain the template's current content."""
    manifests = _load_manifests()
    entry = manifests.get(_sha1(vue_file))
    if entry is not None:
        return entry
    if vue_file.name in _manifest_names:
        raise RuntimeError(f"{vue_file} changed since bundle {_manifest_names[vue_file.name]} was built, rebuild it (see write_bundle_entry)")
    raise RuntimeError(
        f"{vue_file} is not in any of the bundles {_loaded_bundles} (from SOLARA_VUE_BUNDLES); regenerate and rebuild the bundle that should contain it"
    )


def _export_names() -> Dict[Path, str]:
    # the python component name, readable in the entry, the bundle and vue
    # devtools; only a within-bundle name collision (two components with the
    # same function name) gets a content-hash suffix to stay unique
    names: Dict[Path, str] = {}
    seen: Dict[str, Path] = {}
    for vue_file, component_name in _vue_files.items():
        name = re.sub(r"[^a-zA-Z0-9]", "_", component_name)
        if name in seen:
            logging.getLogger("solara").warning(
                "duplicate component name %s (%s and %s); disambiguating with a content-hash suffix", name, seen[name], vue_file
            )
            name = f"{name}_{_sha1(vue_file)[:8]}"
        else:
            seen[name] = vue_file
        names[vue_file] = name
    return names


def write_bundle_entry(directory: Path, name: str = "app-components") -> Path:
    """Write <name>-entry.js and <name>-manifest.json for every component_vue
    template imported so far; returns the entry path. Import the application
    first, then call this, then run the bundler on the entry."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    if not _vue_files:
        raise RuntimeError("no component_vue templates recorded; import the application first")
    lines = []
    exports = []
    components = {}
    export_names = _export_names()
    for i, vue_file in enumerate(_vue_files):
        export = export_names[vue_file]
        relative = pathlib.PurePath(os.path.relpath(vue_file, directory)).as_posix()
        lines.append(f'import _c{i} from "{relative}";')
        # give the component a devtools/debugging name; an explicit name in
        # the SFC wins (spread comes after)
        exports.append(f'export const {export} = {{ name: "{export}", ..._c{i} }};')
        components[str(vue_file)] = {"export": export, "sha1": _sha1(vue_file)}
    lines += [""] + exports
    entry = directory / f"{name}-entry.js"
    entry.write_text("// generated by solara.components.vue_bundle.write_bundle_entry - do not edit\n" + "\n".join(lines) + "\n", encoding="utf8")
    (directory / f"{name}-manifest.json").write_text(json.dumps({"name": name, "components": components}, indent=2) + "\n", encoding="utf8")
    return entry
