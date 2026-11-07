"""Generate a Sphinx (intersphinx) inventory for the Solara API docs.

The API pages call ``apidoc(solara.X)`` to render the docstring of an object.
We parse those calls, so each object maps to the page that documents it.
The result is written to ``solara/website/public/objects.inv``, which the
website serves at https://solara.dev/static/public/objects.inv

Run this after adding or moving an API page:

    python -m solara.website.intersphinx
"""

import ast
import importlib
import re
import types
import zlib
from pathlib import Path
from typing import List, NamedTuple, Optional

HERE = Path(__file__).parent
PAGES = HERE / "pages"
OUTPUT = HERE / "public" / "objects.inv"

HEADER = b"""# Sphinx inventory version 2
# Project: Solara
# Version: latest
# The remainder of this file is compressed using zlib.
"""

# names used in the pages that are not reachable as an attribute of solara
NAME_PREFIXES = {"auth": "solara_enterprise.auth"}


class Entry(NamedTuple):
    name: str
    role: str  # "function" or "class" in the "py" domain
    uri: str


def _dotted_name(node: ast.expr) -> Optional[str]:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _dotted_name(node.value)
        return parent and f"{parent}.{node.attr}"
    return None


def _apidoc_targets(source: str) -> List[str]:
    names = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "apidoc" and node.args:
            name = _dotted_name(node.args[0])
            if name is None:
                raise ValueError(f"Cannot resolve the argument of apidoc: {ast.dump(node.args[0])}")
            names.append(name)
    return names


def _resolve(name: str):
    module_name, _, attr_path = name.partition(".")
    obj = importlib.import_module(module_name)
    for attr in attr_path.split("."):
        try:
            obj = getattr(obj, attr)
        except AttributeError:
            # a submodule that its parent does not import, such as solara.autorouting
            obj = importlib.import_module(f"{obj.__name__}.{attr}")
    return obj


def _names_and_role(name: str):
    """Return all names for the object, the public one first, and its role."""
    if name.endswith(".f"):  # a component, apidoc wants the wrapped function
        name = name[: -len(".f")]
    first, _, rest = name.partition(".")
    if first in NAME_PREFIXES:
        # optional package, do not import it, so the output does not depend on the environment
        return [f"{NAME_PREFIXES[first]}.{rest}"], "function"
    obj = _resolve(name)
    names = [name]
    short = name.rsplit(".", 1)[-1]
    for public_module in ["solara", "solara.lab"]:
        if getattr(importlib.import_module(public_module), short, None) is obj:
            names.insert(0, f"{public_module}.{short}")
            break
    target = getattr(obj, "f", obj)  # the function a component wraps
    module, qualname = getattr(target, "__module__", None), getattr(target, "__qualname__", None)
    if module and qualname and module.startswith("solara"):
        names.append(f"{module}.{qualname}")
    role = "class" if isinstance(obj, type) else "function"
    unique = list(dict.fromkeys(names))
    return unique, role


def _anchor(source: str, short_name: str) -> str:
    # pages that document more objects have a heading per object, and the
    # markdown "toc" extension gives it an id like "inputtextarea"
    if re.search(rf"^\s*(__doc__ \+= \")?#+ {re.escape(short_name)}\b", source, re.MULTILINE):
        return "#" + short_name.lower()
    return ""


def _guess_targets(path: Path, source: str) -> List[str]:
    """For a page without apidoc, match the file name or first heading to a public object."""
    candidates = [] if path.stem.startswith("_") else [path.stem]
    heading = re.search(r"^# (\w+)\s*$", source, re.MULTILINE)
    if heading:
        candidates.append(heading.group(1))
    for candidate in candidates:
        for public_module in ["solara", "solara.lab"]:
            obj = getattr(importlib.import_module(public_module), candidate, None)
            if obj is not None and not isinstance(obj, types.ModuleType):
                return [f"{public_module}.{candidate}"]
    return []


def collect_entries(pages: Path = PAGES) -> List[Entry]:
    entries = []
    for path in sorted((pages / "documentation").rglob("*.py")):
        source = path.read_text(encoding="utf8")
        targets = _apidoc_targets(source) or _guess_targets(path, source)
        relative = path.relative_to(pages).with_suffix("")
        if relative.name == "__init__":
            relative = relative.parent
        page = relative.as_posix()
        for target in targets:
            names, role = _names_and_role(target)
            anchor = _anchor(source, names[0].rsplit(".", 1)[-1]) if len(targets) > 1 else ""
            for name in names:
                entries.append(Entry(name, role, page + anchor))
    return sorted(set(entries))


def inventory_body(entries: List[Entry]) -> bytes:
    lines = [f"{e.name} py:{e.role} 1 {e.uri} -\n" for e in entries]
    return "".join(lines).encode("utf8")


def read_inventory_body(path: Path = OUTPUT) -> bytes:
    data = path.read_bytes()
    assert data.startswith(HEADER), "Unexpected header"
    return zlib.decompress(data[len(HEADER) :])


def write_inventory(path: Path = OUTPUT) -> List[Entry]:
    entries = collect_entries()
    path.write_bytes(HEADER + zlib.compress(inventory_body(entries), 9))
    return entries


if __name__ == "__main__":
    written = write_inventory()
    print(f"Wrote {len(written)} entries to {OUTPUT}")  # noqa: T201
