import importlib
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
    files = dict(vue_bundle._vue_files)
    vue_bundle._vue_files.clear()
    monkeypatch.setattr(vue_bundle, "_exports", None)
    monkeypatch.setattr(vue_bundle, "_root", None)
    monkeypatch.setattr(vue_bundle, "_keys", {})
    monkeypatch.setattr(vue_bundle, "_warned", set())
    try:
        yield
    finally:
        vue_bundle._vue_files.clear()
        vue_bundle._vue_files.update(files)


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
    marker = vue_bundle.EXPORTS_MARKER + " " + ",".join(exports)
    return _write(public / name, f"const c0 = {{}};\nexport {{ {items} }};\n{marker}\n")


def test_entry(clean_state, tmp_path: Path):
    root = tmp_path / "src"
    a = _write(root / "components" / "a.vue", "<template><div>a</div></template>")
    b = _write(root / "b.vue", "<template><div>b</div></template>")
    outside = _write(tmp_path / "lib" / "c.vue", "<template><div>c</div></template>")
    vue_bundle.record(a, "CompA")
    vue_bundle.record(b, "2nd.Comp")
    vue_bundle.record(outside, "Library")

    code = vue_bundle.entry_code(tmp_path / "vue" / "entry.js", root.resolve())
    key_a = vue_bundle.key(a.resolve(), root.resolve())
    assert 'import _c0 from "../src/components/a.vue";' in code
    assert f'export const CompA_{key_a} = {{ name: "CompA", ..._c0 }};' in code
    assert f"export const _2nd_Comp_{vue_bundle.key(b.resolve(), root.resolve())} = " in code
    # library templates (outside the app root) are not bundled
    assert "c.vue" not in code

    # the key covers the path relative to the root and the content
    assert len(key_a) == 12
    copy = _write(root / "other" / "a.vue", a.read_text())
    assert vue_bundle.key(copy.resolve(), root.resolve()) != key_a
    a.write_text("<template><div>a2</div></template>")
    assert vue_bundle.key(a.resolve(), root.resolve()) != key_a


def test_entry_other_drive(clean_state, tmp_path: Path, monkeypatch):
    root = tmp_path / "src"
    vue_bundle.record(_write(root / "a.vue", "<template><div>a</div></template>"), "CompA")

    def relpath(path, start):
        raise ValueError("path is on mount 'D:', start on mount 'C:'")

    monkeypatch.setattr(vue_bundle.os.path, "relpath", relpath)
    monkeypatch.setattr(vue_bundle, "key", lambda file, root: KEY)
    with pytest.raises(RuntimeError, match="same drive"):
        vue_bundle.entry_code(tmp_path / "vue" / "entry.js", root.resolve())


def test_parse_exports():
    marker = f"{vue_bundle.EXPORTS_MARKER} Foo_{KEY},$Bar_ba9876543210,helper"
    code = f"const a={{}},b={{}};export{{a as Foo_{KEY},b as $Bar_ba9876543210}};\n{marker}\n//# sourceMappingURL=app.mjs.map\n"
    assert vue_bundle.parse_exports(code) == {KEY: f"Foo_{KEY}", "ba9876543210": "$Bar_ba9876543210"}
    # export-like text anywhere else does not count, only the marker line
    fake = f'const s = "export {{ a as Fake_aaaaaaaaaaaa }}";\n// export {{ b as Fake_bbbbbbbbbbbb }};\n{marker}\n'
    assert vue_bundle.parse_exports(fake) == {KEY: f"Foo_{KEY}", "ba9876543210": "$Bar_ba9876543210"}
    # built without the solara plugin: no marker
    assert vue_bundle.parse_exports(f"export {{ a as Foo_{KEY} }};\n") is None


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
    _write(public / "empty.mjs", f"export {{ a as Foo }};\n{vue_bundle.EXPORTS_MARKER} Foo\n")
    _write(public / "nomarker.mjs", f"export {{ a as Foo_{KEY} }};\n")
    assert not vue_bundle.load("missing.mjs", tmp_path, public)
    assert not vue_bundle.load("../elsewhere/app.mjs", tmp_path, public)
    assert not vue_bundle.load(str(tmp_path / "elsewhere" / "app.mjs"), tmp_path, public)
    assert not vue_bundle.load("empty.mjs", tmp_path, public)
    assert not vue_bundle.load("nomarker.mjs", tmp_path, public)
    assert defined == []
    assert vue_bundle._exports is None


def test_lookup(clean_state, tmp_path: Path, defined, monkeypatch):
    root = tmp_path / "src"
    a = _write(root / "a.vue", "<template><div>a</div></template>")
    miss = _write(root / "miss.vue", "<template><div>miss</div></template>")
    library = _write(tmp_path / "lib" / "lib.vue", "<template><div>lib</div></template>")
    export = vue_bundle.export_name("A", vue_bundle.key(a.resolve(), root.resolve()))
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


@pytest.mark.parametrize("vuetify", [True, False])
def test_widget(clean_state, tmp_path: Path, defined, monkeypatch, virtual_context, vuetify):
    # a component in pkg/__init__.py is decorated before the server loads the
    # bundle (find_spec runs it), so the choice must happen at widget creation
    root = tmp_path / "pkg"
    vuetify_arg = "True" if vuetify else "False"
    _write(
        root / "__init__.py",
        "import solara\n"
        f"@solara.component_vue('hit.vue', vuetify={vuetify_arg})\n"
        "def Hit(value: int = 0): pass\n"
        f"@solara.component_vue('miss.vue', vuetify={vuetify_arg})\n"
        "def Miss(value: int = 0): pass\n",
    )
    hit = _write(root / "hit.vue", "<template><div>{{ value }}</div></template>")
    _write(root / "miss.vue", "<template><span>{{ value }}</span></template>")
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.delitem(sys.modules, "pkg", raising=False)
    pkg = importlib.import_module("pkg")
    try:
        export = vue_bundle.export_name("Hit", vue_bundle.key(hit.resolve(), root.resolve()))
        _bundle(tmp_path / "public", [export])
        assert vue_bundle.load("vue/app.mjs", vue_bundle.app_root("pkg"), tmp_path / "public")
        monkeypatch.setattr(solara, "_using_solara_server", lambda: True)

        box, rc = solara.render(solara.Column(children=[pkg.Hit(value=1), pkg.Hit(value=2), pkg.Miss(value=3)]), handle_error=False)
        hit1, hit2, miss = box.children[0].children
        assert hit1.template.esm_module == vue_bundle.MODULE_NAME
        assert hit1.template.esm_export == export
        # one Template widget per kernel
        assert hit2.template is hit1.template
        assert miss.template.esm_module is None
        assert miss.template.template == "<template><span>{{ value }}</span></template>"
        rc.close()
    finally:
        sys.modules.pop("pkg", None)


def test_cli(clean_state, tmp_path: Path, monkeypatch):
    from click.testing import CliRunner

    from solara.__main__ import cli

    src = tmp_path / "src"
    _write(src / "app.py", "import solara\n@solara.component_vue('card.vue')\ndef MyCard(value: int = 0): pass\n")
    card = _write(src / "card.vue", "<template><div>card</div></template>")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "path", list(sys.path))
    runner = CliRunner()

    result = runner.invoke(cli, ["vue-bundle", "src/app.py", "-o", "vue/entry.js", "--vite-config"])
    assert result.exit_code == 0, result.output
    export = vue_bundle.export_name("MyCard", vue_bundle.key(card.resolve(), src.resolve()))
    assert f"export const {export} = " in (tmp_path / "vue" / "entry.js").read_text()
    config = (tmp_path / "vue" / "vite.config.mjs").read_text()
    assert 'outDir: "../public/vue"' in config and "publicDir: false" in config
    assert vue_bundle.EXPORTS_MARKER in config and "this.parse(" in config

    check = ["vue-bundle", "src/app.py", "--check", "--bundle", "vue/app.mjs"]
    assert runner.invoke(cli, check).exit_code == 1  # not built yet
    _write(tmp_path / "public" / "vue" / "app.mjs", f"export {{ a as {export} }};\n")
    result = runner.invoke(cli, check)
    assert result.exit_code == 1
    assert "built without solara's vite plugin" in result.output
    _bundle(tmp_path / "public", [export])
    result = runner.invoke(cli, check)
    assert result.exit_code == 0, result.output
    card.write_text("<template><div>edited</div></template>")
    result = runner.invoke(cli, check)
    assert result.exit_code == 1
    assert "card.vue" in result.output


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


def test_cli_package_app(clean_state, tmp_path: Path, monkeypatch):
    # pages of a package app are imported through its routes, not by the package
    from click.testing import CliRunner

    from solara.__main__ import cli

    _write(tmp_path / "mypkg" / "__init__.py", "")
    _write(tmp_path / "mypkg" / "pages" / "__init__.py", "")
    _write(
        tmp_path / "mypkg" / "pages" / "card.py",
        "import solara\n@solara.component_vue('card.vue')\ndef PageCard(value: int = 0): pass\n@solara.component\ndef Page():\n    PageCard()\n",
    )
    card = _write(tmp_path / "mypkg" / "pages" / "card.vue", "<template><div>card</div></template>")
    _write(tmp_path / "other" / "app.py", "import solara\n@solara.component\ndef Page(): pass\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "path", list(sys.path))
    runner = CliRunner()
    try:
        result = runner.invoke(cli, ["vue-bundle", "mypkg.pages:Page", "-o", "vue/entry.js"])
        assert result.exit_code == 0, result.output
        export = vue_bundle.export_name("PageCard", vue_bundle.key(card.resolve(), (tmp_path / "mypkg").resolve()))
        assert f"export const {export} = " in (tmp_path / "vue" / "entry.js").read_text()
        # the selector form also works for scripts
        result = runner.invoke(cli, ["vue-bundle", "other/app.py:Page", "--check", "--bundle", "vue/app.mjs"])
        # no templates under other/: checking nothing must not pass
        assert result.exit_code == 1
        assert "no component_vue templates found" in result.output
    finally:
        for name in list(sys.modules):
            if name == "mypkg" or name.startswith("mypkg."):
                sys.modules.pop(name)
