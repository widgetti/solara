# Design: native HTML components for Solara

**Status:** proposal for upstream discussion
**Scope:** an additional component renderer for standalone Solara apps; the existing Vue renderer and default page shell stay in place

## 1. Problem and boundary

`@solara.component_vue` turns a Python function signature into synchronized widget
traits and callbacks, then renders a Vue template. Solara needs an equivalent way to
author a component with ordinary HTML, CSS, and browser JavaScript. The component
must be a native widget view, not a Vue template with an `.html` extension.

This proposal does not replace Solara's standalone page template, default UI
components, or notebook rendering. An HTML component can coexist with Vue widgets in
the current standalone app. The page still loads Vue for its shell and any Vue widgets.
A browser runtime with no Vue at all would be a separate, opt-in project.

## 2. Existing integration points

- `solara/components/component_vue.py` derives synced traits, `on_<name>` change
  callbacks, and `event_<name>` callbacks from a function signature. Its helper is
  currently Vue-specific: it creates `vue_` event methods despite accepting an
  `event_prefix` argument.
- `solara/server/static/main-vuetify.js` already attaches a non-Vue widget view via
  the widget manager. The new view can be exercised inside today's page shell.
- `solara/server/app.py` renders Reacton elements into widgets. An HTML widget can
  participate in that tree without changing the app entry point.
- `tests/unit/component_frontend_test.py` provides the Python-side callback and
  serializer patterns. Browser behavior needs Playwright integration tests.

## 3. Proposed v1 API

```python
import solara


@solara.component_html("greeting.html")
def Greeting(name: str = "world", on_name=None, event_reset=None):
    pass
```

The HTML file is the single source for markup, scoped CSS, and optional JavaScript.
Its path resolves relative to the decorated Python function's source file, as with
`component_vue`. No CSS or JS argument is required. A component may use standard
CSS `@import` and ES-module `import` statements to reuse shared assets; those
imports are opt-in and are served from the app's public assets. From a component
section, use `../public/shared.css` or `../public/shared.js`: the extracted
section is served under `/static/html-components/`, so these paths resolve under
the app's root path to `/static/public/`. Literal `../public/` URLs in template
attributes such as `src` and `href` are resolved against the same virtual asset
directory by the view; otherwise browser HTML attributes resolve against the page
URL. None of these URLs resolve relative to the original `.html` file. V1 does not add
separate decorator arguments for styles or scripts.

The file has exactly one top-level `<template>` section and may have one top-level
`<style>` and one top-level `<script type="module">` section. The style and script
sections are optional. Other top-level content is an error. This is a deliberately
small single-file component format: its template contains normal HTML rather than
Vue directives or an expression language.

The decorator returns a Reacton element. Ordinary arguments become synchronized
widget traits. As with `component_vue`, `on_<name>` observes changes to the
corresponding widget trait, and `event_<name>` is an explicit callback carrying a JSON
value. The existing `tags`, `to_json`, and `from_json` options should be supported.
Callbacks are never synchronized as widget data. Invalid or missing files fail with
an error that names the resolved path.

### Data flow compared with `component_vue`

The normal state path is the same widget-prop pattern used by Solara's Vue
components. Python passes `name` into the component. The HTML view receives it
as a synchronized widget prop and displays it through an explicit binding such
as `data-solara-text="name"`. To send a new value back, use
`data-solara-model="name"` on a supported form control, or call
`set("name", value)` from the browser module. That changes the widget prop and
calls Python's `on_name` callback. It is analogous to mutating the prop in a
Solara Vue template; it does not use Vue's `$emit`.

Ordinary HTML attributes are static unless a `data-solara-*` binding connects
them to a prop. Local JavaScript variables are never synchronized by themselves.
For example, a component can keep a draft input value in its `mount` closure and
call `set` only on blur, Enter, or after a debounce. The simple
`data-solara-model` binding sends text changes on each `input` event.

The separate `event_reset` argument is for a discrete action. A
`data-solara-event-click="reset"` binding or the module's `emit("reset", data)`
invokes that Python callback; it does not update a prop automatically. The name
`emit` here refers to a Solara widget message, not Vue's `$emit`. The Python
callback can then change application state. Thus state changes use props and
`on_<prop>`; named actions use `event_<name>`.

### HTML binding subset

The `<template>` section is an HTML fragment, not Jinja or Vue. The following attributes are the
complete declarative feature set proposed for v1:

| Attribute | Meaning |
| --- | --- |
| `data-solara-text="name"` | Set `textContent` from prop `name`. |
| `data-solara-attr-title="name"` | Set/remove an allowed HTML attribute from prop `name`; the suffix is the attribute name. |
| `data-solara-prop-disabled="name"` | Set an allowed DOM property such as `disabled` or `checked`. Properties that interpret HTML are excluded. |
| `data-solara-model="name"` | Two-way binding for a text input, textarea, checkbox, or single select. Text uses `input`; checkbox and select use `change`. Values are strings or booleans; numeric parsing requires a controller. |
| `data-solara-event-click="reset"` | Send a DOM event to Python's `event_reset` callback, with `None` as its payload. The suffix is the DOM event name. |

Bindings reference prop names only. There are no expressions, loops, conditionals,
raw-HTML interpolation, or automatic Python callback invocation from arbitrary DOM
events. The JavaScript controller handles behavior beyond this subset.
`data-solara-model` updates the widget model only when the value actually differs, so an incoming
Python update cannot produce a change loop. Browser events are not serialized or
sent wholesale. Controllers construct explicit JSON payloads.

An example `greeting.html` is:

```html
<template>
  <div class="greeting">
    <output data-solara-text="name"></output>
    <input type="text" data-solara-model="name">
    <button type="button" data-solara-event-click="reset">Reset</button>
    <slot></slot>
  </div>
</template>

<style>
  :host { display: block; }
  .greeting { color: var(--app-text-color, #222); }
  /* Shared rules can be imported from a public CSS asset when needed. */
</style>

<script type="module">
  export function mount({ root, set }) {
    const input = root.querySelector("input");
    const onKeydown = (event) => {
      if (event.key === "Escape") set("name", "world");
    };
    input.addEventListener("keydown", onKeydown);
    return () => input.removeEventListener("keydown", onKeydown);
  }
</script>
```

The parser must reject `<script>` elements inside `<template>`, additional top-level
scripts, and inline `on*` event attributes. Values received from Python are inserted as text or DOM
properties/attributes, never interpreted as HTML. The binder must reject `on*`
attributes, HTML-interpreting properties such as `innerHTML`, and unsafe schemes in
URL-valued attributes. Developer-authored HTML and JavaScript are trusted app code.

### Optional JavaScript controller

The inline module exports a `mount` function, called separately for every widget view:

```javascript
export function mount({ root, get, set, subscribe, emit }) {
  // root is this instance's ShadowRoot.
  // get(name) reads a synced prop; set(name, value) changes it and saves it.
  // subscribe(name, listener) observes later changes.
  // emit(name, jsonValue) invokes Python's event_<name> callback.
  return () => {
    // Remove listeners, timers, observers, object URLs, etc.
  };
}
```

The `<script type="module">` body does not execute merely because the template was
inserted into the DOM. Solara must extract it and load it as an ES module; it must
not use `eval`, `new Function`, or a `blob:`/`data:` URL that requires weakening a
site's content security policy. The proposed implementation serves the extracted
module at a content-hashed, same-origin Solara URL and imports that URL.

`mount` may be asynchronous; disposal must await or safely cancel incomplete
initialization. Shared module scope must not hold per-instance state. A controller
file change may trigger a full browser refresh in v1: native custom elements cannot
be redefined in place. Routine prop changes must update existing nodes without
replacing the component root or losing focus.

## 4. Composition and styling

There are two distinct forms of reuse:

1. **Python components.** A decorated function may accept `children`. The trait uses
   standard widget serialization. The browser view creates, attaches, reconciles,
   and disposes child widget views in the component host's light DOM; the template's
   default `<slot>` projects them into the Shadow DOM. This must be tested with both
   an HTML child and an existing widget child. It does not make a Python component
   available automatically as an HTML tag.
2. **Browser-only Custom Elements.** A controller module may import and register
   native elements such as `<app-button>`. Those elements manage their own browser
   properties, events, and styles. They do not have Python widget models unless
   explicitly wrapped by a Python component.

The HTML view uses a Shadow DOM root by default. The file's `<style>` section is
applied inside that root. App-level CSS custom properties can supply shared design tokens;
`::part` and slots expose explicit customization points. Slotted Python children
retain ownership of their own styles. V1 does not include named Python slots or a
Solara-specific custom-element registry.

## 5. Asset and lifecycle policy

- The `.html` file is read as UTF-8. The markup is synchronized with the widget
  model in v1. The extracted CSS and JS are registered by content hash and served
  as `text/css` and `text/javascript` from same-origin URLs under
  `/static/html-components/`. The
  endpoint serves only registered section content, never arbitrary source files.
  It follows the existing static asset authorization policy, and both Starlette
  and Flask adapters need it. The browser caches each hash across
  component instances; a ShadowRoot links the CSS URL, and the view imports the
  JS URL. This avoids inline-script execution and repeated CSS/JS transfer.
- Each instance gets its own `mount` invocation even though the ES module itself
  is imported once per URL. Imported shared assets can be hosted in the app's
  existing `public` directory through the `../public/` relative path. Tests must
  cover that resolution under a nonempty `root_path`.
- Python rerenders update traits on the existing widget. The browser changes only
  bound nodes and properties. When the widget closes, it calls the controller's
  cleanup function, removes subscriptions/listeners, and disposes child views.
- Any component file edit may trigger a full browser refresh in v1 via Solara's
  existing file watcher. Development and installed-wheel behavior must be tested
  separately.

## 6. Implementation slices and acceptance

1. **Single-file loading proof.** Parse the three sections, serve only the
   registered CSS and ES module by content hash, and dynamically import the
   module from the existing standalone page. Test MIME types, a nonempty root
   path, invalid sections, and disposal during an incomplete import. This
   validates the distinctive one-file requirement before changing Reacton code.
2. **Renderer-neutral Python metadata.** Extract only the signature/trait and
   callback behavior shared with `component_vue`; keep Vue event routing in the Vue
   adapter. Unit-test defaults, serializers, rerenders, `on_<name>`, and
   `event_<name>` without a browser.
3. **Native widget view and decorator.** Add the DOMWidget model/view, minimal
   bindings, controller lifecycle, Shadow DOM CSS, and default child slot. Browser
   tests cover Python-to-browser updates, browser-to-Python changes, independent
   instances, focus preservation, child reconciliation, and disposal.
4. **Assets, documentation, and packaging.** Exercise extracted CSS/JS routes,
   public imports under a nonempty root path, browser refresh, an installed wheel,
   and the supported ipywidgets 7 and 8 frontend builds. Document unsupported
   template syntax and the distinction between native components and the Vue page
   shell. Each implementation PR includes its relevant tests and docs.

The existing `component_vue` API and default Solara page must behave exactly as
before. In particular, `component_html` must not cause a Vue component to be
registered or compiled for its own view.

## 7. Questions for upstream review

1. Is the limited `data-solara-*` binding syntax acceptable, or should v1 require
   explicit JavaScript for all dynamic behavior? This proposal favors the limited
   syntax so a simple component needs no build step.
2. Should the extracted CSS/JS endpoint be part of this feature, or should the
   first implementation use a static-file build step? This proposal favors the
   endpoint so a single source file works without a user build step.
3. Is `../public/` an acceptable public import spelling in a section? It follows
   URL resolution from `/static/html-components/` and works under a nonempty root
   path, but ties the authoring convention to the asset URL layout.
