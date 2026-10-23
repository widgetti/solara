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

## Bundling all component_vue templates

Your app code keeps `@solara.component_vue("foo.vue")` as it is. In production, solara can
serve all of the app's templates from one prebuilt ES module instead of their source.
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

    The command imports the app and writes one export per `component_vue` template under the
    app root (the script's directory, or the top-level package of a module). Solara's own
    templates are not in it. Run it again after you add or edit a template.

2. Build it (needs `vite`, `@vitejs/plugin-vue2` or for ipyvue 3 `@vitejs/plugin-vue`, and `vite-plugin-css-injected-by-js`):

    ```bash
    cd vue && npx vite build      # writes public/vue/app.mjs
    ```

3. Run with the bundle, as a path relative to the public directory:

    ```bash
    SOLARA_VUE_BUNDLE=vue/app.mjs solara run src/solara_app.py
    ```

The page preloads the bundle with a versioned url, and solara serves it with an immutable
cache header (see above).

Each export is named `<ComponentName>_<key>`, for example `MyCard_6d0c4e3fef1e`. The key is a
hash of the template's path (relative to the app root) and its content. The `solara-vue-bundle`
plugin in the vite config below writes the export names on the last lines of the built file,
and solara reads them at startup, so there is no manifest. A bundle built without that plugin
is not used. When a widget is created,
solara looks up the key of its template. When the key is not in the bundle, for example
after an edit without a rebuild, solara logs a warning and serves the template source, as
without the setting. A missing or unreadable bundle also falls back to source, with a warning.

Use bundle mode in production only: solara does not watch the templates in this mode, so an
edit needs a rebuild and a restart. Develop with `SOLARA_VUE_BUNDLE` unset. It only has an
effect under the solara server, not in Jupyter.

### The vite config

`--vite-config` writes `vue/vite.config.mjs` only when it does not exist, so you can edit it:

```js
import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue2"; // @vitejs/plugin-vue for ipyvue 3 (vue 3)
import cssInjectedByJs from "vite-plugin-css-injected-by-js";

const solaraVueBundle = {
  name: "solara-vue-bundle",
  enforce: "pre",
  // ipyvue templates use `module.exports = {...}`, an ES module needs `export default`
  transform(code, id) {
    if (!id.endsWith(".vue")) return null;
    // find the script in a copy with html comments blanked out, offsets stay the same
    const masked = code.replace(/<!--[\s\S]*?-->/g, (c) => " ".repeat(c.length));
    const script = /(<script[^>]*>)([\s\S]*?)<\/script>/.exec(masked);
    if (!script) return null;
    const offset = script.index + script[1].length;
    const body = code.slice(offset, offset + script[2].length);
    let ast;
    try {
      ast = this.parse(body);
    } catch {
      return null;
    }
    const isModuleExports = (e) =>
      e.type === "AssignmentExpression" && e.operator === "=" && e.left.type === "MemberExpression" && !e.left.computed &&
      e.left.object.type === "Identifier" && e.left.object.name === "module" && e.left.property.name === "exports";
    const stmt = ast.body.find((s) => s.type === "ExpressionStatement" && isModuleExports(s.expression));
    if (!stmt) return null;
    // replace the whole statement, so parentheses around it or its value stay balanced
    const expr = stmt.expression;
    const value = body.slice(body.indexOf("=", expr.left.end) + 1, expr.end);
    return code.slice(0, offset + stmt.start) + "export default (" + value + ");" + code.slice(offset + stmt.end);
  },
  // solara reads the export names from this line; it goes after the code (and
  // before a sourceMappingURL line), so source map line numbers stay valid
  generateBundle(options, bundle) {
    for (const chunk of Object.values(bundle)) {
      if (chunk.type !== "chunk" || !chunk.isEntry) continue;
      const marker = `// solara-vue-bundle-exports: ${chunk.exports.join(",")}\n`;
      const code = chunk.code.endsWith("\n") ? chunk.code : chunk.code + "\n";
      const at = code.lastIndexOf("\n//# sourceMappingURL=") + 1;
      chunk.code = at > 0 ? code.slice(0, at) + marker + code.slice(at) : code + marker;
    }
  },
};

export default defineConfig({
  // entry and outDir are relative to this file, also for `vite build -c vue/vite.config.mjs`
  root: path.dirname(fileURLToPath(import.meta.url)),
  // css-injected-by-js: lib mode writes a separate .css file that nothing loads
  plugins: [solaraVueBundle, vue(), cssInjectedByJs()],
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

### Check the bundle in CI

```bash
solara vue-bundle src/solara_app.py --check --bundle vue/app.mjs
```

This exits with 1, and lists the templates, when a template of the app is not in the bundle
or the bundle is missing. Without `--bundle`, it uses `SOLARA_VUE_BUNDLE`.

### Limits

- An ES module runs in strict mode. A template that assigns to an undeclared variable at load
  time throws, and one template that throws at load breaks the whole bundle. Load the bundle
  in node in CI, with `vue` stubbed (node 22.15 or later):

    ```js
    // smoke.mjs, run as: node smoke.mjs public/vue/app.mjs
    import { registerHooks } from "node:module";
    const vue = "data:text/javascript,export default {}; export const h = () => null;";
    registerHooks({ resolve: (specifier, context, next) => (specifier === "vue" ? { url: vue, shortCircuit: true } : next(specifier, context)) });
    const bundle = await import(new URL(process.argv[2], `file://${process.cwd()}/`).href);
    console.log(Object.keys(bundle).join("\n"));
    ```

    Add the names your templates import from `vue` to the stub.
- An undeclared variable inside a method fails only when the method runs. Use eslint with
  `no-undef` to find these.
- Only a top-level `module.exports = {...}` statement and `export default {...}` work. The
  `exports.foo = ...` style does not.
- Only templates in modules that the app imports at startup get into the entry. A template in
  a module that the app imports later serves its source.
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
