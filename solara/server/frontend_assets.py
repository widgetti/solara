"""The npm packages of the Solara page, and the URLs of their chunks (one per frontend feature).

The Vue 3 build is @widgetti/solara-vuetify3-app, the Vue 2 build is @widgetti/solara-vuetify-app.
Each has a build per ipywidgets major version (M = 7 or 8) in dist/:

- core JS: solara-vuetify-app{M}.min.js (production) or solara-vuetify-app{M}.js (development)
- feature JS chunks: solara-vuetify-app{M}.{feature}.min.js or .js
- CSS: main{M}.css (core) and main{M}.{feature}.css, the same files in production and development. Vuetify's
  CSS (feature vuetify-css) is main{M}.vuetify.css.

The versions are updated by bumpversion (see packages/*/.bumpversion.cfg).
"""

import dataclasses
from typing import Dict, List, Optional, Tuple

from solara.server import frontend

SOLARA_VUETIFY3_APP_VERSION = "5.2.0"
SOLARA_VUETIFY_APP_VERSION = "10.1.1"

PACKAGES: Dict[bool, Tuple[str, str]] = {
    True: ("@widgetti/solara-vuetify3-app", SOLARA_VUETIFY3_APP_VERSION),
    False: ("@widgetti/solara-vuetify-app", SOLARA_VUETIFY_APP_VERSION),
}


@dataclasses.dataclass(frozen=True)
class Chunk:
    name: str
    # a JS chunk that the page preloads with a <script> tag
    js: bool = False
    # a small JS file that the browser only uses for a lazy load (a CSS-only feature), never preloaded
    stub: bool = False
    # where the CSS link (and its slot for a lazy load) goes: "head-first" (in the head, before the core CSS),
    # "head" (after the core CSS), "body", or None (no CSS)
    css: Optional[str] = None
    # chunks (not features) that must run before this one
    needs: Tuple[str, ...] = ()
    # the CSS file is main{M}.{css_name}.css, when that is not the chunk name (see webpack-plugins.js CSS_NAMES)
    css_name: Optional[str] = None

    @property
    def css_stem(self) -> str:
        return self.css_name or self.name


# A chunk that more than one feature needs. It is not a feature.
SHARED_CHUNKS: Dict[str, Chunk] = {
    "sanitizer": Chunk("sanitizer", js=True),
}

# Chunks that the browser only loads on demand, never preloaded and not a feature: CodeMirror,
# which the markdown renderer of Output widgets uses to highlight code blocks.
LAZY_CHUNKS: Tuple[str, ...] = ("codemirror", "codemirror-modes")

# Per Vue version (key: Vue 3), the chunks in the canonical order: the order of the <script> tags, and
# within "head-first", "head" and "body" the order of the CSS links. Font-awesome and mermaid come from their own
# CDN packages, and vue-sfc from ipyvue, so they are not in this table.
# Vuetify's CSS is the feature vuetify-css, so an app can ship its own. Its file keeps the name main{M}.vuetify.css,
# and its place: on Vue 3 it was the CSS of the vuetify chunk, right after the core CSS; on Vue 2 it was the start of
# the core CSS (main{M}.css), so it comes right before the core CSS there.
CHUNKS: Dict[bool, Tuple[Chunk, ...]] = {
    True: (
        Chunk("vuetify", js=True),
        Chunk("vuetify-css", stub=True, css="head", css_name="vuetify"),
        Chunk("katex", js=True, css="head"),
        Chunk("jupyter-css", stub=True, css="head"),
        Chunk("jquery", js=True),
        Chunk("lumino", js=True),
        Chunk("jupyter-controls", js=True, needs=("sanitizer",)),
        Chunk("output-widget", js=True, needs=("sanitizer",)),
        Chunk("mdi", stub=True, css="body"),
        Chunk("material-icons", stub=True, css="body"),
        Chunk("roboto", stub=True, css="body"),
    ),
    # Vuetify's JS is in the core bundle of the Vue 2 build
    False: (
        Chunk("vuetify-css", stub=True, css="head-first", css_name="vuetify"),
        Chunk("katex", js=True, css="head"),
        Chunk("jupyter-css", stub=True, css="head"),
        Chunk("jquery", js=True),
        Chunk("lumino", js=True),
        Chunk("jupyter-controls", js=True, needs=("sanitizer",)),
        Chunk("output-widget", js=True, needs=("sanitizer",)),
        Chunk("mdi", stub=True, css="body"),
        Chunk("material-icons", stub=True, css="body"),
        Chunk("roboto", stub=True, css="body"),
    ),
}

MERMAID_PATH = "/mermaid@10.8.0/dist/mermaid.min.js"
REQUIREJS_PATH = "/requirejs@2.3.6/require.js"


@dataclasses.dataclass(frozen=True)
class CssLink:
    feature: str
    url: Optional[str]  # None when the feature is not preloaded: the page only has its slot
    data_href: str  # the chunk CSS file name, so the browser knows the chunk CSS is already there
    # the name of the slot: the browser finds it from the CSS file name main{M}.{slot}.css (slotInsert in
    # solara-widget-manager/webpack-plugins.js), e.g. "vuetify" for feature vuetify-css
    slot: str


@dataclasses.dataclass(frozen=True)
class FrontendAssets:
    package: str
    version: str
    base: str
    core_js: str
    core_css: str
    # the CSS links before the core CSS
    head_first_css: List[CssLink]
    head_css: List[CssLink]
    body_css: List[CssLink]
    chunk_js: List[str]
    # the names of the chunks in chunk_js
    chunk_names: List[str]


def base_url(vue3: bool, cdn: str) -> str:
    package, version = PACKAGES[vue3]
    return f"{cdn}/{package}@{version}/dist/"


def js_file(feature: str, ipywidgets_major: int, production: bool) -> str:
    """feature "core" is the main bundle."""
    return f"solara-vuetify-app{ipywidgets_major}" + ("" if feature == "core" else f".{feature}") + (".min" if production else "") + ".js"


def css_file(feature: str, ipywidgets_major: int) -> str:
    """feature "core" is the main CSS. CSS does not depend on production."""
    return f"main{ipywidgets_major}" + ("" if feature == "core" else f".{feature}") + ".css"


def chunks(vue3: bool) -> Dict[str, Chunk]:
    return {chunk.name: chunk for chunk in CHUNKS[vue3]}


def page_assets(vue3: bool, ipywidgets_major: int, production: bool, cdn: str, enabled: frontend.Frontend) -> FrontendAssets:
    package, version = PACKAGES[vue3]
    base = base_url(vue3, cdn)

    def css_link(chunk: Chunk) -> CssLink:
        name = css_file(chunk.css_stem, ipywidgets_major)
        return CssLink(feature=chunk.name, url=base + name if chunk.name in enabled else None, data_href=name, slot=chunk.css_stem)

    chunk_names: List[str] = []
    for chunk in CHUNKS[vue3]:
        if chunk.js and chunk.name in enabled:
            for name in (*chunk.needs, chunk.name):
                if name not in chunk_names:
                    chunk_names.append(name)
    return FrontendAssets(
        package=package,
        version=version,
        base=base,
        core_js=base + js_file("core", ipywidgets_major, production),
        core_css=base + css_file("core", ipywidgets_major),
        head_first_css=[css_link(chunk) for chunk in CHUNKS[vue3] if chunk.css == "head-first"],
        head_css=[css_link(chunk) for chunk in CHUNKS[vue3] if chunk.css == "head"],
        body_css=[css_link(chunk) for chunk in CHUNKS[vue3] if chunk.css == "body"],
        chunk_js=[base + js_file(name, ipywidgets_major, production) for name in chunk_names],
        chunk_names=chunk_names,
    )


def dist_files(vue3: bool, ipywidgets_major: int, production: bool) -> List[str]:
    """Every JS and CSS file name the build writes to dist/ for this configuration (for tests)."""
    names = [js_file("core", ipywidgets_major, production), css_file("core", ipywidgets_major)]
    for name in (*SHARED_CHUNKS, *LAZY_CHUNKS):
        names.append(js_file(name, ipywidgets_major, production))
    for chunk in CHUNKS[vue3]:
        if chunk.js or chunk.stub:
            names.append(js_file(chunk.name, ipywidgets_major, production))
        if chunk.css:
            names.append(css_file(chunk.css_stem, ipywidgets_major))
    return names
