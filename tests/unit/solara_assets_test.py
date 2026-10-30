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
    info = _assets_info()
    content_hashes = info["content_hashes"]
    last_version, last_hash = list(content_hashes.items())[-1]
    assert last_hash == content_hash, (
        "The assets in packages/solara-assets/hatch_build.py changed. "
        "Bump __version__ in packages/solara-assets/solara_assets2/__init__.py, "
        f"add the new version with hash {content_hash!r} to content_hashes, and update the solara-assets2 pin in packages/solara-meta/pyproject.toml"
    )
    assert last_version == info["__version__"], "The last entry of content_hashes must be for __version__"
    # a new hash under an existing version would not be published, because the release skips existing versions
    assert len(set(content_hashes.values())) == len(content_hashes), "Each version in content_hashes needs a new hash"


def test_assets_pinned_by_meta_package():
    version = _assets_info()["__version__"]
    pyproject = (root / "packages" / "solara-meta" / "pyproject.toml").read_text(encoding="utf8")
    assert re.findall(r'"solara-assets2==([^"]+)"', pyproject) == [version]
