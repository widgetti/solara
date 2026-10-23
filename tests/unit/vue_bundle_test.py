import json
import os
import sys
from pathlib import Path

import pytest

import solara
from solara.components import vue_bundle

ipyvue = pytest.importorskip("ipyvue")

if not hasattr(ipyvue, "define_module"):
    pytest.skip("requires ipyvue with ES module support", allow_module_level=True)

from solara.server import kernel_context  # noqa: E402
from solara.server.kernel import Kernel  # noqa: E402

KEY = "0123456789ab"


@pytest.fixture()
def clean_state(monkeypatch):
    monkeypatch.setattr(vue_bundle, "_exports", None)
    monkeypatch.setattr(vue_bundle, "_root", None)
    monkeypatch.setattr(vue_bundle, "_keys", {})
    monkeypatch.setattr(vue_bundle, "_warned", set())


@pytest.fixture()
def defined(monkeypatch):
    calls = []
    monkeypatch.setattr(ipyvue, "define_module", lambda name, **kwargs: calls.append((name, kwargs)))
    return calls


@pytest.fixture()
def virtual_context():
    context = kernel_context.VirtualKernelContext(id="vue-bundle-test", kernel=Kernel(), session_id="session-vue-bundle")
    try:
        with context:
            yield context
    finally:
        context.close()


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def _bundle(public: Path, exports, name="vue/app.mjs") -> Path:
    items = ", ".join(f"c{i} as {export}" for i, export in enumerate(exports))
    _write(public / (name + ".json"), json.dumps({"exports": list(exports)}))
    return _write(public / name, f"const c0 = {{}};\nexport {{ {items} }};\n")


def test_entry(clean_state, tmp_path: Path):
    root = tmp_path / "src"
    a = _write(root / "components" / "transcript-entry.vue", "<template><div>a</div></template>")
    b = _write(root / "2nd.vue", "<template><div>b</div></template>")
    _write(root / "node_modules" / "dep" / "dep.vue", "<template><div>dep</div></template>")
    _write(root / ".cache" / "hidden.vue", "<template><div>hidden</div></template>")
    _write(tmp_path / "lib" / "lib.vue", "<template><div>lib</div></template>")

    # every .vue under the root, sorted, without node_modules and hidden dirs
    assert vue_bundle.app_templates(root) == [b.resolve(), a.resolve()]
    code = vue_bundle.entry_code(tmp_path / "vue" / "entry.js", root)
    key_a = vue_bundle.key(a.resolve(), root.resolve())
    assert 'import _c0 from "../src/2nd.vue";' in code
    assert 'import _c1 from "../src/components/transcript-entry.vue";' in code
    assert f'export const transcript_entry_{key_a} = {{ name: "transcript_entry", ..._c1 }};' in code
    assert f'export const _2nd_{vue_bundle.key(b.resolve(), root.resolve())} = {{ name: "_2nd", ..._c0 }};' in code
    assert "dep.vue" not in code and "hidden.vue" not in code and "lib.vue" not in code

    # the key covers the path relative to the root and the content
    assert len(key_a) == 12
    copy = _write(root / "other" / "transcript-entry.vue", a.read_text())
    assert vue_bundle.key(copy.resolve(), root.resolve()) != key_a
    a.write_text("<template><div>a2</div></template>")
    assert vue_bundle.key(a.resolve(), root.resolve()) != key_a


def test_entry_other_drive(clean_state, tmp_path: Path, monkeypatch):
    root = tmp_path / "src"
    _write(root / "a.vue", "<template><div>a</div></template>")

    def relpath(path, start):
        raise ValueError("path is on mount 'D:', start on mount 'C:'")

    monkeypatch.setattr(vue_bundle.os.path, "relpath", relpath)
    monkeypatch.setattr(vue_bundle, "key", lambda file, root: KEY)
    with pytest.raises(RuntimeError, match="same drive"):
        vue_bundle.entry_code(tmp_path / "vue" / "entry.js", root.resolve())


def test_manifest(tmp_path: Path):
    manifest = json.dumps({"exports": [f"Foo_{KEY}", "$Bar_ba9876543210", "helper"]})
    assert vue_bundle.parse_manifest(manifest) == {KEY: f"Foo_{KEY}", "ba9876543210": "$Bar_ba9876543210"}
    for invalid in ["{", "[]", '{"exports": "Foo"}', "{}"]:
        assert vue_bundle.parse_manifest(invalid) is None
    bundle = _bundle(tmp_path, [f"Foo_{KEY}"])
    assert vue_bundle.read_manifest(bundle) == {KEY: f"Foo_{KEY}"}
    (tmp_path / "vue" / "app.mjs.json").unlink()
    assert vue_bundle.read_manifest(bundle) is None


def test_load(clean_state, tmp_path: Path, defined):
    public = tmp_path / "public"
    _bundle(public, [f"Foo_{KEY}"])
    assert vue_bundle.load("vue/app.mjs", tmp_path / "src", public)
    assert defined == [(vue_bundle.MODULE_NAME, {"url": "/static/public/vue/app.mjs"})]
    assert vue_bundle._exports == {KEY: f"Foo_{KEY}"}
    # absolute paths are fine when inside the public dir
    assert vue_bundle.load(str(public / "vue" / "app.mjs"), tmp_path / "src", public)


def test_load_falls_back_to_source(clean_state, tmp_path: Path, defined):
    public = tmp_path / "public"
    _write(tmp_path / "elsewhere" / "app.mjs", f"export {{ a as Foo_{KEY} }};")
    _bundle(public, ["Foo"], name="empty.mjs")
    _write(public / "nomanifest.mjs", f"export {{ a as Foo_{KEY} }};\n")
    _bundle(public, [f"Foo_{KEY}"], name="invalid.mjs")
    _write(public / "invalid.mjs.json", "{")
    assert not vue_bundle.load("missing.mjs", tmp_path, public)
    assert not vue_bundle.load("../elsewhere/app.mjs", tmp_path, public)
    assert not vue_bundle.load(str(tmp_path / "elsewhere" / "app.mjs"), tmp_path, public)
    assert not vue_bundle.load("empty.mjs", tmp_path, public)
    assert not vue_bundle.load("nomanifest.mjs", tmp_path, public)
    assert not vue_bundle.load("invalid.mjs", tmp_path, public)
    assert defined == []
    assert vue_bundle._exports is None


def test_lookup(clean_state, tmp_path: Path, defined, monkeypatch):
    root = tmp_path / "src"
    a = _write(root / "a.vue", "<template><div>a</div></template>")
    miss = _write(root / "miss.vue", "<template><div>miss</div></template>")
    library = _write(tmp_path / "lib" / "lib.vue", "<template><div>lib</div></template>")
    export = vue_bundle.export_name(a, vue_bundle.key(a.resolve(), root.resolve()))
    _bundle(tmp_path / "public", [export])
    assert vue_bundle.load("vue/app.mjs", root, tmp_path / "public")

    monkeypatch.setattr(solara, "_using_solara_server", lambda: False)
    assert vue_bundle.lookup(a) is None
    monkeypatch.setattr(solara, "_using_solara_server", lambda: True)
    assert vue_bundle.lookup(a) == export
    assert vue_bundle.lookup(miss) is None
    assert vue_bundle.lookup(library) is None
    assert vue_bundle.lookup(root / "deleted.vue") is None  # OSError
    assert vue_bundle._warned == {miss}


def _load_bundle(root: Path, public: Path, files, monkeypatch):
    exports = [vue_bundle.export_name(file, vue_bundle.key(file.resolve(), root.resolve())) for file in files]
    _bundle(public, exports)
    assert vue_bundle.load("vue/app.mjs", root, public)
    monkeypatch.setattr(solara, "_using_solara_server", lambda: True)
    return exports


def test_get_template(clean_state, tmp_path: Path, defined, monkeypatch, virtual_context):
    # the patched get_template serves every template file: component_vue and template_file widgets
    root = tmp_path / "src"
    hit = _write(root / "hit.vue", "<template><div>{{ value }}</div></template>")
    miss = _write(root / "miss.vue", "<template><span>{{ value }}</span></template>")
    (export,) = _load_bundle(root, tmp_path / "public", [hit], monkeypatch)
    from ipyvue import VueTemplate

    class FileWidget(VueTemplate):
        template_file = str(hit)

    class MissWidget(VueTemplate):
        template_file = (str(root / "app.py"), "miss.vue")

    widget = FileWidget()
    assert (widget.template.esm_module, widget.template.esm_export) == (vue_bundle.MODULE_NAME, export)
    # one Template widget per kernel
    assert FileWidget().template is widget.template
    assert MissWidget().template.esm_module is None
    assert MissWidget().template.template == miss.read_text()

    for vuetify in [True, False]:
        component = solara._component_vue(str(hit), vuetify=vuetify)(lambda value=0: None)
        box, rc = solara.render(component(value=1), handle_error=False)
        assert box.children[0].template is widget.template
        rc.close()


def test_register_component_from_file(clean_state, tmp_path: Path, defined, monkeypatch, virtual_context):
    if not hasattr(ipyvue, "register_component_from_esm"):
        pytest.skip("requires ipyvue with register_component_from_esm")
    from ipyvue.VueComponentRegistry import vue_component_files, vue_component_registry

    root = tmp_path / "src"
    hit = _write(root / "components" / "hit.vue", "<template><div>hit</div></template>")
    miss = _write(root / "components" / "miss.vue", "<template><div>miss</div></template>")
    (export,) = _load_bundle(root, tmp_path / "public", [hit], monkeypatch)
    app = str(root / "app.py")

    ipyvue.register_component_from_file("hit-component", "components/hit.vue", app)
    component = vue_component_registry["hit-component"]
    assert (component.esm_module, component.esm_export, component.component) == (vue_bundle.MODULE_NAME, export, "")
    # the old argument order: (None, name, file)
    ipyvue.register_component_from_file(None, "hit-old", str(hit))
    assert vue_component_registry["hit-old"].esm_export == export

    ipyvue.register_component_from_file("miss-component", "components/miss.vue", app)
    component = vue_component_registry["miss-component"]
    assert component.esm_module is None
    assert component.component == miss.read_text()
    # source components keep their bookkeeping for hot reload
    assert vue_component_files[os.path.abspath(str(miss))] == "miss-component"
    assert os.path.abspath(str(hit)) not in vue_component_files


def test_cli(clean_state, tmp_path: Path, monkeypatch):
    from click.testing import CliRunner

    from solara.__main__ import cli

    src = tmp_path / "src"
    # the app is not imported: a component registered at render time counts too
    _write(src / "app.py", "raise RuntimeError('not imported')\n")
    card = _write(src / "card.vue", "<template><div>card</div></template>")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "path", list(sys.path))
    runner = CliRunner()

    result = runner.invoke(cli, ["vue-bundle", "src/app.py:Page", "-o", "vue/entry.js", "--vite-config"])
    assert result.exit_code == 0, result.output
    export = vue_bundle.export_name(card, vue_bundle.key(card.resolve(), src.resolve()))
    assert f"export const {export} = " in (tmp_path / "vue" / "entry.js").read_text()
    config = (tmp_path / "vue" / "vite.config.mjs").read_text()
    assert 'outDir: "../public/vue"' in config and "publicDir: false" in config
    assert "emitFile(" in config and "this.parse(" in config
    assert "__solaraStyle" in config and "transformAssetUrls: false" in config

    check = ["vue-bundle", "src/app.py", "--check", "--bundle", "vue/app.mjs"]
    assert runner.invoke(cli, check).exit_code == 1  # not built yet
    _write(tmp_path / "public" / "vue" / "app.mjs", f"export {{ a as {export} }};\n")
    result = runner.invoke(cli, check)
    assert result.exit_code == 1
    # rich wraps long lines (long tmp paths in CI)
    assert "no app.mjs.json next to the bundle" in " ".join(result.output.split())
    _bundle(tmp_path / "public", [export])
    result = runner.invoke(cli, check)
    assert result.exit_code == 0, result.output
    card.write_text("<template><div>edited</div></template>")
    result = runner.invoke(cli, check)
    assert result.exit_code == 1
    assert "card.vue" in " ".join(result.output.split())
    # checking nothing must not pass
    _write(tmp_path / "empty" / "app.py", "")
    result = runner.invoke(cli, ["vue-bundle", "empty/app.py", "--check", "--bundle", "vue/app.mjs"])
    assert result.exit_code == 1
    assert "no .vue files found" in " ".join(result.output.split())


def test_app_root_namespace_package(clean_state, tmp_path: Path, monkeypatch):
    # a top-level namespace package (no __init__.py) has no origin
    _write(tmp_path / "nsroot" / "myapp" / "app.py", "")
    monkeypatch.syspath_prepend(str(tmp_path))
    try:
        assert vue_bundle.app_root("nsroot.myapp.app") == (tmp_path / "nsroot" / "myapp").resolve()
    finally:
        for name in ["nsroot", "nsroot.myapp", "nsroot.myapp.app"]:
            sys.modules.pop(name, None)


def test_load_error_keeps_server_up(clean_state, tmp_path: Path, monkeypatch, no_kernel_context):
    from solara.server import app as appmod

    _write(tmp_path / "app.py", "import solara\n@solara.component\ndef Page():\n    solara.Text('hi')\n")

    def broken(*args, **kwargs):
        raise RuntimeError("broken bundle")

    monkeypatch.setattr(vue_bundle, "load", broken)
    monkeypatch.setattr(solara.settings.main, "vue_bundle", "vue/app.mjs")
    app_script = appmod.AppScript(str(tmp_path / "app.py"))
    try:
        app_script.init()
    finally:
        app_script.close()
    assert vue_bundle._exports is None
