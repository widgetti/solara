"""Serve the app's .vue templates from one prebuilt ES module.

`solara vue-bundle app.py -o vue/entry.js` writes a vite entry with one export
per .vue file under the app root. The export name is `<file stem>_<key>`,
where key is a hash of the file's path (relative to the app root) and content.
The vite build writes the export names to <bundle>.json next to the bundle,
and the server reads them. Solara's patched get_template and
register_component_from_file look a file up by its key, so component_vue,
template_file widgets and registered components all use the bundle, and a
file whose key is missing (edited after the build) falls back to source.

Solara's own (library) templates are never bundled.
"""

import fnmatch
import hashlib
import json
import logging
import os
import re
import sys
from pathlib import Path, PurePath
from typing import Dict, List, Optional, Sequence, Set

import solara

logger = logging.getLogger("solara.components.vue_bundle")

MODULE_NAME = "solara-vue-bundle"
BUNDLE_FILE_NAME = "app.mjs"

# the loaded bundle: key -> export name, or None when bundle mode is off
_exports: Optional[Dict[str, str]] = None
_root: Optional[Path] = None
_keys: Dict[Path, Optional[str]] = {}
_warned: Set[Path] = set()

_EXPORT_NAME = re.compile(r"^[A-Za-z_$][\w$]*_([0-9a-f]{12})$")
# an export list, optionally a re-export: export { a as Foo_<key>, b } from "x";
# the last lines of a bundle built with the starter vite config
NO_MANIFEST = "no %s.json next to the bundle; build it with solara's vite plugin (see `solara vue-bundle --vite-config`)"


def app_root(app: str) -> Path:
    """The directory whose templates belong to the app: the script's (or
    notebook's) directory, the directory itself, or the top-level package of a
    module. Used by the CLI and the server, so both agree on the keys."""
    path = Path(app)
    if app.endswith(".py") or app.endswith(".ipynb"):
        return path.resolve().parent
    if path.is_dir():
        return path.resolve()
    import importlib.util

    # only the top-level name: find_spec of a dotted name runs the parent packages
    spec = importlib.util.find_spec(app.split(".")[0])
    if spec is None or spec.origin is None:
        # a namespace package has no single root: use the app module's directory
        spec = importlib.util.find_spec(app)
        if spec is None or spec.origin is None:
            raise ImportError(f"Module {app} cannot be found")
    return Path(spec.origin).resolve().parent


def public_dir(app: str) -> Path:
    """The dir solara serves at /static/public for the app (as AppScript does)."""
    path = Path(app)
    if app.endswith(".py") or app.endswith(".ipynb"):
        directory = path.resolve().parent
    elif path.is_dir():
        directory = path.resolve()
    else:
        import importlib.util

        spec = importlib.util.find_spec(app)
        if spec is None or spec.origin is None:
            raise ImportError(f"Module {app} cannot be found")
        directory = Path(spec.origin).resolve().parent
    return directory.parent / "public"


def key(vue_file: Path, root: Path) -> str:
    relative = PurePath(os.path.relpath(vue_file, root)).as_posix()
    content = vue_file.read_bytes()
    return hashlib.sha1(relative.encode("utf8") + b"\0" + content).hexdigest()[:12]  # noqa: S324 - content id, not security


def _identifier(name: str) -> str:
    name = re.sub(r"[^A-Za-z0-9_$]", "_", name)
    return "_" + name if not name or name[0].isdigit() else name


def export_name(vue_file: Path, key: str) -> str:
    return f"{_identifier(vue_file.stem)}_{key}"


def _inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


# never app templates: installed packages and tool dirs (a venv inside the app root
# would put every library template in the bundle)
_SKIP_DIRS = {"node_modules", "__pycache__", "site-packages", "dist-packages"}


def app_templates(root: Path, exclude: Sequence[str] = ()) -> List[Path]:
    """Every .vue file under the app root, sorted. Skips node_modules, hidden dirs,
    __pycache__, virtual envs and site-packages, and paths (relative to the root)
    that match an exclude glob."""
    root = root.resolve()

    def excluded(relative: str) -> bool:
        return any(fnmatch.fnmatch(relative, pattern) for pattern in exclude)

    templates = []
    for directory, dirs, files in os.walk(root):
        base = Path(directory)
        dirs[:] = [
            name
            for name in dirs
            if not (name in _SKIP_DIRS or name.startswith(".") or (base / name / "pyvenv.cfg").exists())
            and not excluded((base / name).relative_to(root).as_posix())
        ]
        templates += [base / name for name in files if name.endswith(".vue") and not excluded((base / name).relative_to(root).as_posix())]
    return sorted(templates)


def entry_code(entry: Path, root: Path, exclude: Sequence[str] = ()) -> str:
    entry = entry.resolve()
    root = root.resolve()
    lines = ["// generated by `solara vue-bundle`, do not edit"]
    exports = []
    for i, vue_file in enumerate(app_templates(root, exclude)):
        name = export_name(vue_file, key(vue_file, root))
        try:
            relative = PurePath(os.path.relpath(vue_file, entry.parent)).as_posix()
        except ValueError:  # windows: another drive
            raise RuntimeError(f"the entry {entry} and the template {vue_file} must be on the same drive")
        if not relative.startswith("."):
            relative = "./" + relative
        lines.append(f'import _c{i} from "{relative}";')
        # a readable name in vue devtools; an explicit name in the SFC wins
        # the export name (unique) as vue name: a plain stem can equal a global component's
        # tag and make the template render itself; an explicit name in the SFC wins
        exports.append(f'export const {name} = {{ name: "{name}", ..._c{i} }};')
    return "\n".join(lines + [""] + exports) + "\n"


_VITE_CONFIG = r"""// starter config written by `solara vue-bundle --vite-config`; solara never overwrites it
import { createHash } from "node:crypto";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import vue from "%(vue_plugin)s";
import cssInjectedByJs from "vite-plugin-css-injected-by-js";
%(sfc_parser)s

// ipyvue.scoped_css_support when this config was written: without it, ipyvue treats
// <style scoped> as a global style
const SCOPED_CSS_SUPPORT = %(scoped_css_support)s;

// added to each template with a style, to apply it as ipyvue's source mode does: only when a
// component is first created (injecting all css at load leaks global rules), into one
// element per id, updated when the css differs
const STYLE_HELPER = `
function __solaraStyle(c, id, css) {
  const mixin = { beforeCreate() {
    let style = document.getElementById(id);
    if (!style) {
      style = document.createElement("style");
      style.id = id;
      document.head.appendChild(style);
    }
    if (style.innerHTML !== css) style.innerHTML = css;
  } };
  c.mixins = [...(c.mixins || []), mixin];
  return c;
}
`;

const ROOT = path.dirname(fileURLToPath(import.meta.url));
// embed text in js, also inside a <script> block
const js = (value) => JSON.stringify(value).replace(/</g, "\\u003c");

const solaraVueBundle = {
  name: "solara-vue-bundle",
  enforce: "pre",
  transform(code, id) {
    if (!id.endsWith(".vue")) return null;
    // the top-level blocks, as ipyvue reads them with vue's sfc parser
    const { script, styles } = parseSfc(code);
    // like ipyvue: only the first <style> counts; lang styles (and scoped ones, with scoped
    // css support) stay with plugin-vue and css-injected-by-js
    const [first, ...ignored] = styles;
    let style = null;
    if (first && !(first.attrs.lang && first.attrs.lang !== "css") && !(first.attrs.scoped && SCOPED_CSS_SUPPORT)) {
      // the path relative to this config, so the id is the same wherever the project lives
      const relative = path.relative(ROOT, id).split(path.sep).join("/");
      const hash = createHash("sha1").update(relative).digest("hex").slice(0, 8);
      const cssId = typeof first.attrs.id === "string" && first.attrs.id;
      // ipyvue's element id; without an id, one element per file (ipyvue: one per view)
      style = { id: cssId ? `ipyvue-${cssId}` : `ipyvue-solara-vue-bundle-${path.basename(id, ".vue")}-${hash}`, css: first.content };
    }
    // blank removed blocks, tags included, so all offsets stay valid
    const removed = style ? [first, ...ignored] : ignored;
    const blank = (text, blocks) =>
      blocks.reduce((t, b) => {
        const [start, end] = [t.lastIndexOf("<style", b.start), t.indexOf(">", b.end) + 1];
        return t.slice(0, start) + t.slice(start, end).replace(/[^\n]/g, " ") + t.slice(end);
      }, text);
    const wrap = (value) => (style ? `__solaraStyle(${value}, ${js(style.id)}, ${js(style.css)})` : value);
    const helper = style ? STYLE_HELPER : "";
    if (!script) {
      if (!removed.length) return null;
      return blank(code, removed) + (style ? `\n<script>\nexport default ${wrap("{}")};\n${helper}</script>\n` : "");
    }
    const [offset, body] = [script.start, script.content];
    const replace = (start, end, text) => {
      const source = blank(code, removed);
      return source.slice(0, offset + start) + text + source.slice(offset + end, offset + body.length) + helper + source.slice(offset + body.length);
    };
    let ast;
    try {
      ast = this.parse(body);
    } catch {
      // ipyvue's fallback for a script that does not run: the object from the first `{`
      const start = body.indexOf("{");
      const legacy = "export default " + body.slice(start);
      try {
        if (start < 0) return null;
        const declaration = this.parse(legacy).body[0].declaration;
        const value = legacy.slice(declaration.start, declaration.end);
        // ipyvue returns that object, the rest of the script never runs
        return replace(0, body.length, `\nexport default ${wrap("(" + value + ")")};\n`);
      } catch {
        return null;
      }
    }
    // ipyvue templates use `module.exports = {...}`, an ES module needs `export default`
    const isModuleExports = (e) =>
      e.type === "AssignmentExpression" && e.operator === "=" && e.left.type === "MemberExpression" && !e.left.computed &&
      e.left.object.type === "Identifier" && e.left.object.name === "module" && e.left.property.name === "exports";
    const stmt = ast.body.find((s) => s.type === "ExpressionStatement" && isModuleExports(s.expression));
    const esm = ast.body.find((s) => s.type === "ExportDefaultDeclaration");
    if (stmt) {
      // replace the whole statement, so parentheses around it or its value stay balanced
      const value = body.slice(stmt.expression.right.start, stmt.expression.right.end);
      return replace(stmt.start, stmt.end, `export default ${wrap("(" + value + ")")};`);
    }
    if (esm) {
      const declaration = body.slice(esm.declaration.start, esm.declaration.end);
      return style ? replace(esm.declaration.start, esm.declaration.end, wrap("(" + declaration + ")")) : ignored.length ? blank(code, ignored) : null;
    }
    const named = ast.body.some((s) => s.type === "ExportNamedDeclaration" && s.specifiers.some((x) => (x.exported.name || x.exported.value) === "default"));
    if (named) {
      // a default export that cannot be wrapped: leave the first style to plugin-vue
      return ignored.length ? blank(code, ignored) : null;
    }
    // no default export: ipyvue uses {}, and the style still goes in on first use
    return replace(body.length, body.length, `\nexport default ${wrap("{}")};\n`);
  },
  // solara reads the export names from <bundle>.json, written by the same build
  generateBundle(options, bundle) {
    for (const chunk of Object.values(bundle)) {
      if (chunk.type !== "chunk" || !chunk.isEntry) continue;
      this.emitFile({ type: "asset", fileName: chunk.fileName + ".json", source: JSON.stringify({ exports: chunk.exports }, null, 2) + "\n" });
    }
  },
};

export default defineConfig({
  // entry and outDir are relative to this file, also for `vite build -c vue/vite.config.mjs`
  root: ROOT,
  plugins: [
    solaraVueBundle,
    // ipyvue does not rewrite <img src="/static/...">, so plugin-vue must not turn them into imports;
    // whitespace as vue's in-browser compiler (source mode) handles it
    vue({ template: { transformAssetUrls: false, compilerOptions: { whitespace: "%(whitespace)s" } } }),
    // lang (and supported scoped) styles: lib mode writes a separate .css file that nothing loads
    cssInjectedByJs(),
  ],
  // the out dir is inside the app's public dir, do not copy it into itself
  publicDir: false,
  build: {
    outDir: "%(out_dir)s",
    emptyOutDir: true,
    lib: { entry: "%(entry)s", formats: ["es"], fileName: () => "%(file_name)s" },
    rollupOptions: {
      // ipyvue provides vue through the import map
      external: ["vue"],
      output: { inlineDynamicImports: true },
    },
  },
});
"""


# the sfc parser of the vue version ipyvue runs; blocks get the offsets of their content
_SFC_PARSER_VUE2 = """import { parseComponent } from "vue/compiler-sfc";

const parseSfc = (code) => {
  const { script, styles } = parseComponent(code);
  return { script, styles };
};"""
_SFC_PARSER_VUE3 = """import { parse } from "@vue/compiler-sfc";

const parseSfc = (code) => {
  const { descriptor } = parse(code);
  const block = (b) => b && { start: b.loc.start.offset, end: b.loc.end.offset, attrs: b.attrs, content: b.content };
  return { script: block(descriptor.script), styles: descriptor.styles.map(block) };
};"""


def vite_config(entry: str, out_dir: str) -> str:
    import ipyvue

    # ipyvue 3 runs vue 3, ipyvue 1 runs vue 2
    vue3 = int(ipyvue.__version__.split(".")[0]) >= 3
    vue_plugin = "@vitejs/plugin-vue" if vue3 else "@vitejs/plugin-vue2"
    scoped_css_support = "true" if getattr(ipyvue, "scoped_css_support", False) else "false"
    return _VITE_CONFIG % {
        "entry": entry,
        "out_dir": out_dir,
        "file_name": BUNDLE_FILE_NAME,
        "vue_plugin": vue_plugin,
        "scoped_css_support": scoped_css_support,
        # the default of each vue version's runtime compiler; plugin-vue2 condenses
        "whitespace": "condense" if vue3 else "preserve",
        "sfc_parser": _SFC_PARSER_VUE3 if vue3 else _SFC_PARSER_VUE2,
    }


def parse_manifest(text: str) -> Optional[Dict[str, str]]:
    """Map key -> export name, from the <bundle>.json that the starter vite
    config writes, or None when it is not valid."""
    try:
        names = json.loads(text)["exports"]
    except (ValueError, TypeError, KeyError):
        return None
    if not isinstance(names, list):
        return None
    return {found.group(1): name for name in names if isinstance(name, str) for found in [_EXPORT_NAME.match(name)] if found}


def read_manifest(bundle: Path) -> Optional[Dict[str, str]]:
    try:
        return parse_manifest(bundle.with_name(bundle.name + ".json").read_text(encoding="utf8"))
    except OSError:
        return None


def resolve_bundle(setting: str, public_dir: Path) -> Optional[Path]:
    """The bundle file for the setting (relative to the served public dir, or
    absolute inside it), or None when it is outside the public dir."""
    public_dir = public_dir.resolve()
    path = Path(setting)
    if not path.is_absolute():
        path = public_dir / path
    path = path.resolve()
    return path if _inside(path, public_dir) else None


def load(setting: Optional[str], root: Path, public_dir: Path) -> bool:
    """Turn bundle mode on for the app at root, and define the module.

    Runs once at server startup. On any problem, warn and keep source mode."""
    global _exports, _root
    if not setting:
        return False
    import ipyvue

    if not hasattr(ipyvue, "define_module"):
        logger.warning("SOLARA_VUE_BUNDLE needs ipyvue with ES module support, serving template source")
        return False
    path = resolve_bundle(setting, public_dir)
    if path is None:
        logger.warning("SOLARA_VUE_BUNDLE=%s is not inside %s, serving template source", setting, public_dir)
        return False
    if not path.is_file():
        logger.warning("SOLARA_VUE_BUNDLE=%s not found, serving template source", path)
        return False
    exports = read_manifest(path)
    if exports is None:
        logger.warning("%s: " + NO_MANIFEST + ", serving template source", path, path.name)
        return False
    if not exports:
        logger.warning("%s has no solara vue-bundle exports, serving template source", path)
        return False
    url = "/static/public/" + path.relative_to(public_dir.resolve()).as_posix()
    # through the module attribute: solara server patches define_module
    ipyvue.define_module(MODULE_NAME, url=url)
    _exports = exports
    _root = root.resolve()
    _keys.clear()
    logger.info("serving %d component_vue templates from %s", len(exports), url)
    return True


def lookup(vue_file: Path) -> Optional[str]:
    """The bundle export for a template, or None to serve its source."""
    if _exports is None or _root is None or not solara._using_solara_server():
        return None
    if vue_file not in _keys:
        file_key = None
        resolved = vue_file.resolve()
        if _inside(resolved, _root):
            try:
                file_key = key(resolved, _root)
            except OSError:
                pass
        # production only: templates do not change while the server runs
        _keys[vue_file] = file_key
    file_key = _keys[vue_file]
    if file_key is None:
        return None
    export = _exports.get(file_key)
    if export is None and vue_file not in _warned:
        _warned.add(vue_file)
        logger.warning("%s is not in the vue bundle (edited or not imported by `solara vue-bundle`), serving its source", vue_file)
    return export


def esm_template(abs_path: str):
    """The shared ESM Template for a template file in the bundle, or None.

    Called from solara's patched ipyvue get_template, so component_vue and
    template_file widgets both use it."""
    export = lookup(Path(abs_path))
    if export is None:
        return None
    import ipyvue as vue

    # per kernel under solara server; the key is not a path, so a file change
    # (AppScript.on_file_change) never touches it
    registry = sys.modules["ipyvue.Template"].template_registry  # type: ignore
    registry_key = f"{MODULE_NAME}:{export}"
    if registry_key not in registry:
        registry[registry_key] = vue.Template(esm_module=MODULE_NAME, esm_export=export)
    return registry[registry_key]


def patch_register_component_from_file(register_component_from_file):
    """Wrap ipyvue's register_component_from_file: a .vue file in the bundle
    registers the bundle export instead of its source."""
    import ipyvue

    def wrapper(name, file_name, relative_to_file=None):
        component_name, file, relative = name, file_name, relative_to_file
        # the same resolution as ipyvue, including its old argument order
        if component_name is None:
            component_name, file, relative = file_name, relative_to_file, None
        if relative:
            file = os.path.join(os.path.dirname(relative), file)
        export = lookup(Path(os.path.abspath(file)))
        if export is None:
            return register_component_from_file(name, file_name, relative_to_file)
        return ipyvue.register_component_from_esm(component_name, MODULE_NAME, export)

    return wrapper
