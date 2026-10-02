# solara-html

Single-file HTML components for Solara, as a separate package.
It is a small demo that this needs almost no change in Solara itself: no server routes, no template edits, no monkey patches.
It needs one public hook, `solara.server.reload.watch_file`, for hot reload.
That hook ships with Solara 1.64.0, so install that release or later.

## API

```python
import solara_html

@solara_html.component_html("greeting.html")
def Greeting(name="World", on_name=None, event_reset=None, children=[]):
    pass
```

The signature works like `solara.component_vue`:

- A plain argument (`name`) becomes a prop that syncs both ways.
- `on_<prop>` is called when the browser changes that prop.
- `event_<name>` is an action the browser can call.
- `children` are Solara widgets, shown at the template's `<slot>`. `children=None` and `children=[]` both work.

Some names are reserved, and the decorator raises a `ValueError` for them:

- names on `ipyreact.Widget`, such as `props`, `events`, `layout`, and `open`, and names that start with `_`;
- two arguments that give the same React prop: ipyreact adds a `set<Name>` setter per prop, so `x` collides with `setX` and with `X`;
- a prop and an event with the same name, such as `click` and `event_click`.

The HTML file has a required `<template>`, an optional `<style>` (scoped, through Shadow DOM), and an optional `<script type="module">`.
See [example/greeting.html](example/greeting.html).

## Bindings

- `data-solara-text="name"` sets the text content.
- `data-solara-model="name"` syncs a text input, textarea, or checkbox (values are strings or booleans).
- `data-solara-attr-title="name"` sets or removes an attribute.
- `data-solara-event-click="reset"` calls `event_reset(None)`.

A binding to an unknown prop or event logs a warning in the browser console.
A bound URL in `href`, `src`, `action`, `formaction`, `poster`, `data`, or `xlink:href` must be relative or use `http`, `https`, `mailto`, or `tel`.
Other URLs are removed, with a warning.
Only these attributes are checked, so do not bind an untrusted value to another attribute that takes a URL or code, such as the SVG `<animate to>`.
Bindings to `srcdoc` and to `on*` attributes are refused, with a warning.

The module script can export `mount({root, get, set, subscribe, emit})` for anything the bindings do not cover.
It can return a cleanup function, or a Promise of one.
`emit("reset")` without data calls `event_reset(None)`.
`set` and `emit` with an unknown name log a warning.

## Relative imports

The module script can import other files relative to the HTML file:

```js
import { characters } from "./format.js";
```

Each imported file becomes its own ES module, and its own relative imports work the same way.
These forms are rewritten: `import x from "./a.js"`, `import "./a.js"`, and `export ... from "./a.js"`.
A dynamic `import("./a.js")` is not rewritten, so it does not work.
Imports inside comments and strings are left as they are.
Regular expression literals are not understood: a quote or `//` inside one can hide the imports after it.
An import inside a nested template literal, such as `` `${`import "./a.js"`}` ``, is still rewritten.
A missing file or an import cycle raises a `ValueError`.

## Hot reload

In development mode (`solara run` without `--production`), a change to the HTML file or to a file it imports reloads the app, like a change to a Python file.
The reload runs the decorator again only when the component is defined in a file under the app's directory.

## How it works

It runs on [ipyreact](https://github.com/widgetti/ipyreact) ES modules, which Solara already supports:

1. At import, the package defines one shared ES module, `solara-html` ([runtime.js](solara_html/runtime.js)), with `ipyreact.define_module`.
2. The decorator turns each `.html` file into its own ES module: the file's script, plus an export that passes the template and CSS to the runtime.
   Each relatively imported file becomes an ES module too, defined before the module that imports it.
   A module is named by a hash of its code, so an edit shows up live after a hot reload.
   Each edit defines a new module; old ones stay until the server restarts (only in development mode, where files change).
3. Each component instance is an `ipyreact.Widget` that names that module.
   ipyreact waits until the module is loaded before it renders, and passes the traits, setters, events, and children to it as React props.
4. The runtime renders a `div`, attaches a shadow root with the template and CSS, and wires the bindings.
   Children stay in the light DOM, so the browser shows them at the `<slot>`.

The browser receives each component's code once per page, not once per instance.

## Limits

- It runs in the Solara server. It is not tested in Jupyter.
- React loads on the page next to Vue.
- Page-wide CSS resets (such as Vuetify's `* { padding: 0 }`) beat `:host` rules, so put spacing on an element inside the template.

## Run the example

```bash
uv venv --python 3.11
uv pip install -e ".[dev]"
uv run playwright install chromium   # only for the check
uv run solara run example/greeting_app.py
uv run python example/check.py --url http://localhost:8765   # in a second shell
```
