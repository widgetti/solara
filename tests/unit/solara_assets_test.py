import ast
import hashlib
import json
import re
from pathlib import Path

root = Path(__file__).parent.parent.parent
assets_dir = root / "packages" / "solara-assets"


def _literal_assignments(path: Path):
    tree = ast.parse(path.read_text(encoding="utf8"))
    return {
        target.id: ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign) for target in node.targets if isinstance(target, ast.Name)
    }


def _assets_info():
    # we parse instead of import, so we do not need hatchling installed
    return _literal_assignments(assets_dir / "solara_assets2" / "__init__.py")


def test_assets_content_hash():
    build = _literal_assignments(assets_dir / "hatch_build.py")
    content = {name: build[name] for name in ["packages", "PRUNE_PATTERNS_ALL", "PRUNE_PATTERNS_PER_PACKAGE"]}
    content_hash = hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()[:16]
    assert _assets_info()["content_hash"] == content_hash, (
        "The assets in packages/solara-assets/hatch_build.py changed. "
        "Bump __version__ in packages/solara-assets/solara_assets2/__init__.py, "
        f"change content_hash to {content_hash!r}, and update the solara-assets2 pin in packages/solara-meta/pyproject.toml"
    )


def test_assets_pinned_by_meta_package():
    version = _assets_info()["__version__"]
    pyproject = (root / "packages" / "solara-meta" / "pyproject.toml").read_text(encoding="utf8")
    assert re.findall(r'"solara-assets2==([^"]+)"', pyproject) == [version]
