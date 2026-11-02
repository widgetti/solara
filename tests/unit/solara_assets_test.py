import ast
import importlib.util
import re
import unittest.mock
import zipfile
from pathlib import Path

root = Path(__file__).parent.parent.parent
assets_dir = root / "packages" / "solara-assets"

spec = importlib.util.spec_from_file_location("solara_assets_check_version", assets_dir / "check_version.py")
assert spec is not None and spec.loader is not None
check_version = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_version)


def _write_wheel(path: Path, record: str):
    with zipfile.ZipFile(path, "w") as wheel:
        wheel.writestr("solara_assets2-1.0.0.dist-info/RECORD", record)


def test_assets_pinned_by_meta_package():
    # we parse instead of import, because solara_assets2 is not installed
    tree = ast.parse((assets_dir / "solara_assets2" / "__init__.py").read_text(encoding="utf8"))
    versions = {
        target.id: ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign) for target in node.targets if isinstance(target, ast.Name)
    }
    pyproject = (root / "packages" / "solara-meta" / "pyproject.toml").read_text(encoding="utf8")
    assert re.findall(r'"solara-assets2==([^"]+)"', pyproject) == [versions["__version__"]]


def test_check_version_compares_file_hashes(tmp_path: Path):
    record_name = "solara_assets2-1.0.0.dist-info/RECORD"
    base = f"a.js,sha256=aaa,1\nb.js,sha256=bbb,1\n{record_name},,\n"
    _write_wheel(tmp_path / "base.whl", base)
    published = check_version.wheel_files(tmp_path / "base.whl")
    assert published == {"a.js": "sha256=aaa", "b.js": "sha256=bbb"}
    assert check_version.differences(published, published) == []

    _write_wheel(tmp_path / "changed.whl", f"a.js,sha256=zzz,1\nc.js,sha256=ccc,1\n{record_name},,\n")
    changed = check_version.wheel_files(tmp_path / "changed.whl")
    assert check_version.differences(changed, published) == ["a.js", "b.js", "c.js"]


def test_check_version_main(tmp_path: Path):
    record_name = "solara_assets2-1.0.0.dist-info/RECORD"
    built = tmp_path / "solara_assets2-1.0.0-py3-none-any.whl"
    same = tmp_path / "same.whl"
    changed = tmp_path / "changed.whl"
    _write_wheel(built, f"a.js,sha256=aaa,1\n{record_name},,\n")
    _write_wheel(same, f"a.js,sha256=aaa,1\n{record_name},,\n")
    _write_wheel(changed, f"a.js,sha256=zzz,1\n{record_name},,\n")

    def main_with_published(url):
        with unittest.mock.patch.object(check_version, "published_wheel_url", return_value=url) as mock:
            result = check_version.main(str(built))
        mock.assert_called_once_with("1.0.0")
        return result

    assert main_with_published(None) == 0
    assert main_with_published(same.as_uri()) == 0
    assert main_with_published(changed.as_uri()) == 1
