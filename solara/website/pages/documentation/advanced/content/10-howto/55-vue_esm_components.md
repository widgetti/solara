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
    """
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

`define_module` also accepts a **url** (a plain `str` always means a url; use `code=` for
inline source). Serve the built bundle from your app's `public/` directory and pass the url:

```python
ipyvue.define_module("my-components", "/static/public/my-components.mjs")
```

For urls solara serves itself this enables aggressive caching without staleness:

- the page emits `<link rel="modulepreload" href=".../my-components.mjs?v=<content-hash>">`,
  so the browser fetches the bundle in parallel with kernel startup;
- the widget uses the **same versioned url**, so the preload is always a cache hit;
- solara serves the file with `Cache-Control: max-age=1y, immutable` when the requested
  hash matches — a rebuild changes the hash and therefore the url, so caches never go stale.

The same applies to ipyreact modules. During development, prefer the `Path` form: the file
is watched, so a bundler in watch mode gives in-place hot reload.

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
