---
title: Using precompiled Vue components (ES modules)
description: Ship ahead-of-time compiled Vue single file components, with npm dependencies bundled in, instead of compiling templates in the browser.
---
# How can I use precompiled Vue components?

Note: this requires ipyvue with ES module support (the vue3 series).

Normally, [`@solara.component_vue`](/documentation/api/utilities/component_vue) sends the `.vue`
template source to the browser, where it is compiled at runtime. Alternatively, you can compile
your `.vue` files **ahead of time** into a single ES module with a bundler like [vite](https://vitejs.dev):

- npm dependencies get compiled into the bundle (no CDN or window-global tricks needed),
- no template source goes over the wire, and no runtime template compiler is needed,
- the components are plain Vue code, checkable with `vue-tsc` and reusable outside solara.

## A complete runnable example

`ipyvue.define_module` accepts the module source as a string or a `Path`, so a minimal
example does not even need a build step:

```python
from typing import Callable

import ipyvue
import solara

ipyvue.define_module(
    "my-components",
    code="""
    import { h } from "vue";

    export const Counter = {
        data: () => ({ count: 0 }),  // placeholder, the real value comes from Python
        methods: {
            bump() {},  // placeholder, solara injects the event_bump handler
        },
        render() {
            return h(
                "button",
                { class: "my-counter", onClick: () => this.bump(1) },
                `clicked ${this.count} times`,
            );
        },
    };
    """,
)


@solara.component_vue(esm_module="my-components", esm_export="Counter")
def Counter(count: int = 0, event_bump: Callable[[int], None] = None):
    pass


@solara.component
def Page():
    count = solara.use_reactive(0)
    Counter(count=count.value, event_bump=lambda amount: count.set(count.value + amount))
```

This works exactly like a [`@solara.component_vue`](/documentation/api/utilities/component_vue)
component backed by a `.vue` file: arguments become Vue data (overriding the component's own
`data()` placeholders) and `event_*` arguments become callable methods, because the component's
options are merged under ipyvue's model mixin with the same precedence as a browser-compiled
template.

## Building real .vue files with vite

For actual applications, keep your components as `.vue` single file components and build them:

```js
// vite.config.mjs
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  plugins: [vue()],
  build: {
    lib: { entry: "src/index.js", formats: ["es"], fileName: () => "my-components.mjs" },
    // vue is provided by ipyvue via the import map
    rollupOptions: { external: ["vue"] },
  },
});
```

```js
// src/index.js — npm dependencies (e.g. canvas-confetti) simply get bundled
export { default as Dashboard } from "./dashboard.vue";
export { default as Toggle } from "./toggle.vue";
```

```python
from pathlib import Path

import ipyvue

ipyvue.define_module("my-components", Path(__file__).parent / "dist/my-components.mjs")
```

Under `solara run`, the bundle file is watched: run `vite build --watch` next to the server
and every save of a `.vue` file rebuilds the bundle and hot reloads the page in place.

## Serving the bundle by url (production)

`define_module` also accepts an explicit **url** keyword (next to `module` for a `Path` and
`code=` for inline source). Serve the built bundle from your app's `public/` directory and pass the url:

```python
ipyvue.define_module("my-components", url="/static/public/my-components.mjs")
```

For urls solara serves itself this enables aggressive caching without staleness:

- the page emits `<link rel="modulepreload" href=".../my-components.mjs?v=<content-hash>">`,
  so the browser fetches the bundle in parallel with kernel startup;
- the widget uses the **same versioned url**, so the preload is always a cache hit;
- solara serves the file with `Cache-Control: max-age=1y, immutable` when the requested
  hash matches — a rebuild changes the hash and therefore the url, so caches never go stale.

The same applies to ipyreact modules. During development, prefer the `Path` form: the file
is watched, so a bundler in watch mode gives in-place hot reload.

## Bundling all .vue files of an app

Your app code stays as it is. In production, solara can serve all of the app's `.vue` files
from one prebuilt ES module instead of their source. This covers
[`@solara.component_vue`](/documentation/api/utilities/component_vue) components,
`ipyvue.VueTemplate` widgets with a `template_file`, and components registered with
`ipyvue.register_component_from_file`, also when the app registers them at render time.
Solara defines the module itself (named `solara-vue-bundle`), so the app never calls
`define_module` for it.

For a layout like this:

```
src/solara_app.py      # the app, with its .vue files under src/
vue/                   # the vite project (package.json, node_modules)
public/                # served at /static/public
```

1. Write the vite entry, and a starter vite config the first time:

    ```bash
    solara vue-bundle src/solara_app.py -o vue/entry.js --vite-config
    ```

    The command does not import the app. It writes one export for every `.vue` file under the
    app root (the script's directory, or the top-level package of a module), sorted, without
    `node_modules` and hidden directories. Solara's own templates are not in it. Run it again
    after you add, rename or remove a `.vue` file.

2. Build it (needs `vite`, `@vitejs/plugin-vue2` or for ipyvue 3 `@vitejs/plugin-vue`, and `vite-plugin-css-injected-by-js`):

    ```bash
    cd vue && npx vite build      # writes public/vue/app.mjs and public/vue/app.mjs.json
    ```

3. Run with the bundle, as a path relative to the public directory:

    ```bash
    SOLARA_VUE_BUNDLE=vue/app.mjs solara run src/solara_app.py
    ```

The page preloads the bundle with a versioned url, and solara serves it with an immutable
cache header (see above).

Each export is named after the file: `<file stem>_<key>`, for example
`transcript_entry_6d0c4e3fef1e` for `transcript-entry.vue`. The key is a hash of the file's
path (relative to the app root) and its content. The `solara-vue-bundle`
plugin in the vite config below writes the export names to `app.mjs.json` in the same build,
and solara reads that file at startup. Deploy `app.mjs` and `app.mjs.json` together. Without
the `.json` file, solara does not use the bundle. When ipyvue loads a template file or
registers a component file, solara looks up the key of that file. When the key is not in the
bundle, for example
after an edit without a rebuild, solara logs a warning and serves the template source, as
without the setting. A missing or unreadable bundle also falls back to source, with a warning.

Use bundle mode in production only: solara does not watch the templates in this mode, so an
edit needs a rebuild and a restart. Develop with `SOLARA_VUE_BUNDLE` unset. It only has an
effect under the solara server, not in Jupyter.

### The vite config

`--vite-config` writes `vue/vite.config.mjs` only when it does not exist, so you can edit it:

```js
import { createHash } from "node:crypto";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue2"; // @vitejs/plugin-vue for ipyvue 3 (vue 3)
import cssInjectedByJs from "vite-plugin-css-injected-by-js";

// ipyvue.scoped_css_support when this config was written: without it, ipyvue treats
// <style scoped> as a global style
const SCOPED_CSS_SUPPORT = false;

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

const solaraVueBundle = {
  name: "solara-vue-bundle",
  enforce: "pre",
  transform(code, id) {
    if (!id.endsWith(".vue")) return null;
    // find blocks in a copy with html comments blanked out, offsets stay the same
    const masked = code.replace(/<!--[\s\S]*?-->/g, (c) => " ".repeat(c.length));
    const script = /(<script[^>]*>)([\s\S]*?)<\/script>/.exec(masked);
    const inScript = (i) => script && i >= script.index && i < script.index + script[0].length;
    // like ipyvue: only the first <style> counts; lang styles (and scoped ones, with scoped
    // css support) stay with plugin-vue and css-injected-by-js
    const [first, ...ignored] = [...masked.matchAll(/<style(\s[^>]*)?>([\s\S]*?)<\/style>/g)].filter((m) => !inScript(m.index));
    let style = null;
    if (first) {
      const attrs = first[1] || "";
      const lang = /(?:^|\s)lang\s*=\s*["']?([\w-]+)/.exec(attrs);
      const scoped = /(?:^|\s)scoped(?=[\s=]|$)/.test(attrs);
      if (!(lang && lang[1] !== "css") && !(scoped && SCOPED_CSS_SUPPORT)) {
        const styleId = /(?:^|\s)id\s*=\s*["']([^"']*)["']/.exec(attrs);
        const hash = createHash("sha1").update(id).digest("hex").slice(0, 8);
        const start = first.index + "<style".length + attrs.length + 1;
        style = {
          // ipyvue's element id; without an id, one element per file (ipyvue: one per view)
          id: styleId ? `ipyvue-${styleId[1]}` : `ipyvue-solara-vue-bundle-${path.basename(id, ".vue")}-${hash}`,
          css: code.slice(start, start + first[2].length),
        };
      }
    }
    // blank the removed blocks, so all offsets stay valid
    const removed = style ? [first, ...ignored] : ignored;
    const blank = (text, blocks) =>
      blocks.reduce((t, m) => t.slice(0, m.index) + t.slice(m.index, m.index + m[0].length).replace(/[^\n]/g, " ") + t.slice(m.index + m[0].length), text);
    const wrap = (value) => (style ? `__solaraStyle(${value}, ${JSON.stringify(style.id)}, ${JSON.stringify(style.css)})` : value);
    if (!script) {
      if (!removed.length) return null;
      return blank(code, removed) + (style ? `\n<script>\nexport default ${wrap("{}")};\n${STYLE_HELPER}</script>\n` : "");
    }
    const offset = script.index + script[1].length;
    const body = code.slice(offset, offset + script[2].length);
    let ast;
    try {
      ast = this.parse(body);
    } catch {
      return null;
    }
    // ipyvue templates use `module.exports = {...}`, an ES module needs `export default`
    const isModuleExports = (e) =>
      e.type === "AssignmentExpression" && e.operator === "=" && e.left.type === "MemberExpression" && !e.left.computed &&
      e.left.object.type === "Identifier" && e.left.object.name === "module" && e.left.property.name === "exports";
    let start, end, replacement;
    const stmt = ast.body.find((s) => s.type === "ExpressionStatement" && isModuleExports(s.expression));
    const esm = ast.body.find((s) => s.type === "ExportDefaultDeclaration");
    if (stmt) {
      // replace the whole statement, so parentheses around it or its value stay balanced
      const value = body.slice(stmt.expression.right.start, stmt.expression.right.end);
      [start, end, replacement] = [stmt.start, stmt.end, `export default ${wrap("(" + value + ")")};`];
    } else if (esm && style) {
      const declaration = body.slice(esm.declaration.start, esm.declaration.end);
      [start, end, replacement] = [esm.declaration.start, esm.declaration.end, wrap("(" + declaration + ")")];
    } else {
      // no default export to attach the style to: leave the first block to plugin-vue
      return ignored.length ? blank(code, ignored) : null;
    }
    const scriptEnd = offset + body.length;
    const source = blank(code, removed);
    return (
      source.slice(0, offset + start) + replacement + source.slice(offset + end, scriptEnd) +
      (style ? STYLE_HELPER : "") + source.slice(scriptEnd)
    );
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
  root: path.dirname(fileURLToPath(import.meta.url)),
  plugins: [
    solaraVueBundle,
    // ipyvue does not rewrite <img src="/static/...">, so plugin-vue must not turn them into imports;
    // whitespace as vue's in-browser compiler (source mode) handles it
    vue({ template: { transformAssetUrls: false, compilerOptions: { whitespace: "preserve" } } }),
    // lang (and supported scoped) styles: lib mode writes a separate .css file that nothing loads
    cssInjectedByJs(),
  ],
  // the out dir is inside the app's public dir, do not copy it into itself
  publicDir: false,
  build: {
    outDir: "../public/vue",
    emptyOutDir: true,
    lib: { entry: "entry.js", formats: ["es"], fileName: () => "app.mjs" },
    rollupOptions: {
      // ipyvue provides vue through the import map
      external: ["vue"],
      output: { inlineDynamicImports: true },
    },
  },
});
```

`emptyOutDir` clears `public/vue` only, so keep other files out of it.

Styles follow the rules of ipyvue's source mode. Only the first `<style>` block of a file
counts. The plugin takes it out of the CSS of the bundle, and inserts it into the page when a
component of that template is first created. With an `id` attribute, the element id is
`ipyvue-<id>`, as in source mode, so templates with the same id share one element. Without an
id, source mode adds one element per view and removes it with the view; the bundle adds one
element per file and keeps it. `<style scoped>` is a global style too, unless
`ipyvue.scoped_css_support` was on when `--vite-config` wrote the config
(`SCOPED_CSS_SUPPORT`). Then scoped styles, like `lang` styles, go into the page when the
bundle loads, which is safe because they cannot leak. Urls such as `<img src="/static/...">` stay as they are, as in source mode.

### Check the bundle in CI

```bash
solara vue-bundle src/solara_app.py --check --bundle vue/app.mjs
```

This exits with 1, and lists the files, when a `.vue` file under the app root is not in the
bundle, when there are no `.vue` files, or when the bundle is missing. Without `--bundle`, it uses `SOLARA_VUE_BUNDLE`.

### Limits

- An ES module runs in strict mode. A template that assigns to an undeclared variable at load
  time throws, and one template that throws at load breaks the whole bundle. Load the bundle
  in node in CI, with `vue` stubbed (node 22.15 or later):

    ```js
    // smoke.mjs, run as: node smoke.mjs public/vue/app.mjs
    import { registerHooks } from "node:module";
    const vue = "data:text/javascript,export default {}; export const h = () => null;";
    registerHooks({ resolve: (specifier, context, next) => (specifier === "vue" ? { url: vue, shortCircuit: true } : next(specifier, context)) });
    // templates can touch browser globals at load: accept any use of window and document
    const stub = new Proxy(function () {}, { get: (t, k) => (k === Symbol.toPrimitive ? () => "" : stub), apply: () => stub, construct: () => stub });
    globalThis.window = globalThis.document = stub;
    const bundle = await import(new URL(process.argv[2], `file://${process.cwd()}/`).href);
    console.log(Object.keys(bundle).join("\n"));
    ```

    Add the names your templates import from `vue`, and the browser globals they use at load,
    to the stubs.
- An undeclared variable inside a method fails only when the method runs. Use eslint with
  `no-undef` to find these.
- Only a top-level `module.exports = {...}` statement and `export default {...}` work. The
  `exports.foo = ...` style does not.
- The url gets the root path when solara runs under a root path with the starlette server.

## Using a precompiled component as a tag

An export can also be used as a tag inside any other template via the `components` dict.
In that form no model mixin is applied — the component keeps its own props/emits contract:

```python
class MyWidget(ipyvue.VueTemplate):
    template = traitlets.Unicode(
        """
        <template>
            <my-toggle :value="enabled" @input="on_input"></my-toggle>
        </template>
        """
    ).tag(sync=True)
    enabled = traitlets.Bool(False).tag(sync=True)
    components = traitlets.Dict(
        {"my-toggle": {"esm_module": "my-components", "esm_export": "Toggle"}}
    ).tag(sync=True, **widget_serialization)

    def vue_on_input(self, value):
        self.enabled = value
```
