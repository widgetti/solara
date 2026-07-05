import json
from pathlib import Path

import pytest

from solara.components import vue_bundle

ipyvue = pytest.importorskip("ipyvue")


@pytest.fixture()
def clean_state(monkeypatch):
    files = list(vue_bundle._vue_files)
    vue_bundle._vue_files.clear()
    vue_bundle._manifests = None
    vue_bundle._manifest_names.clear()
    monkeypatch.delenv("SOLARA_VUE_BUNDLES", raising=False)
    try:
        yield
    finally:
        vue_bundle._vue_files.clear()
        vue_bundle._vue_files.extend(files)
        vue_bundle._manifests = None
        vue_bundle._manifest_names.clear()


def _make_template(tmp_path: Path, name: str, source: str) -> Path:
    file = tmp_path / "app" / "components" / name
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(source)
    return file


def test_write_entry_and_manifest(clean_state, tmp_path: Path):
    a = _make_template(tmp_path, "a.vue", "<template><div>a</div></template>")
    b = _make_template(tmp_path, "b.vue", "<template><div>b</div></template>")
    vue_bundle.record(a)
    vue_bundle.record(b)

    entry = vue_bundle.write_bundle_entry(tmp_path / "bundle", name="test-components")
    lines = entry.read_text().splitlines()
    assert any('from "../app/components/a.vue";' in line for line in lines)
    assert any(line.startswith("export const c_a_") and 'name: "a"' in line for line in lines)
    manifest = json.loads((tmp_path / "bundle" / "test-components-manifest.json").read_text())
    assert manifest["name"] == "test-components"
    entry_a = next(v for k, v in manifest["components"].items() if k.endswith("a.vue"))
    assert entry_a["export"].startswith("c_a_")
    assert entry_a["sha1"] == vue_bundle._sha1(a)


def test_lookup_by_content_hash(clean_state, tmp_path: Path, monkeypatch):
    a = _make_template(tmp_path, "a.vue", "<template><div>a</div></template>")
    vue_bundle.record(a)
    vue_bundle.write_bundle_entry(tmp_path / "bundle", name="test-components")
    monkeypatch.setenv("SOLARA_VUE_BUNDLES", str(tmp_path / "bundle" / "test-components-manifest.json"))
    vue_bundle._manifests = None

    assert vue_bundle.enabled()
    assert vue_bundle.lookup(a)[0] == "test-components" and vue_bundle.lookup(a)[1].startswith("c_a_")

    # stale: content changed after the bundle was generated
    a.write_text("<template><div>a2</div></template>")
    with pytest.raises(RuntimeError, match="changed since bundle"):
        vue_bundle.lookup(a)

    # missing: never bundled
    c = _make_template(tmp_path, "c.vue", "<template><div>c</div></template>")
    with pytest.raises(RuntimeError, match="not in any bundle"):
        vue_bundle.lookup(c)


@pytest.mark.skipif(not hasattr(ipyvue, "define_module"), reason="needs ipyvue with ES module support")
def test_component_vue_uses_bundle(clean_state, tmp_path: Path, monkeypatch):
    a = _make_template(tmp_path, "a.vue", "<template><div>{{ value }}</div></template>")
    vue_bundle.record(a)
    vue_bundle.write_bundle_entry(tmp_path / "bundle", name="test-components")
    monkeypatch.setenv("SOLARA_VUE_BUNDLES", str(tmp_path / "bundle" / "test-components-manifest.json"))
    vue_bundle._manifests = None

    from solara.components.component_vue import _widget_vue

    # simulate what @component_vue does for a template resolved via the bundle
    module, export = vue_bundle.lookup(a)
    assert module == "test-components" and export.startswith("c_a_")

    @_widget_vue(None, esm_module=module, esm_export=export)
    def Widget(value: int = 0):
        pass

    widget = Widget(value=3)
    assert widget.template.esm_module == "test-components"
    assert widget.template.esm_export == export
