"""The npm packages of the Solara page, and the URLs of their chunks (one per frontend feature).

The Vue 3 build is @widgetti/solara-vuetify3-app, the Vue 2 build is @widgetti/solara-vuetify-app.
Each has a build per ipywidgets major version (M = 7 or 8) in dist/:

- core JS: solara-vuetify-app{M}.min.js (production) or solara-vuetify-app{M}.js (development)
- feature JS chunks: solara-vuetify-app{M}.{feature}.min.js or .js
- CSS: main{M}.css (core) and main{M}.{feature}.css, the same files in production and development

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
    # where the CSS link (and its slot for a lazy load) goes: "head", "body", or None (no CSS)
    css: Optional[str] = None
    # chunks (not features) that must run before this one
    needs: Tuple[str, ...] = ()


# A chunk that more than one feature needs. It is not a feature.
SHARED_CHUNKS: Dict[str, Chunk] = {
    "sanitizer": Chunk("sanitizer", js=True),
}

# Chunks that the browser only loads on demand, never preloaded and not a feature: CodeMirror,
# which the markdown renderer of Output widgets uses to highlight code blocks.
LAZY_CHUNKS: Tuple[str, ...] = ("codemirror", "codemirror-modes")

# Per Vue version (key: Vue 3), the chunks in the canonical order: the order of the <script> tags, and
# within "head" and "body" the order of the CSS links. Font-awesome and mermaid come from their own
# CDN packages, and vue-sfc from ipyvue, so they are not in this table.
CHUNKS: Dict[bool, Tuple[Chunk, ...]] = {
    True: (
        Chunk("vuetify", js=True, css="head"),
        Chunk("katex", js=True, css="head"),
        Chunk("jupyter-css", stub=True, css="head"),
        Chunk("jupyter-controls", js=True, needs=("sanitizer",)),
        Chunk("output-widget", js=True, needs=("sanitizer",)),
        Chunk("mdi", stub=True, css="body"),
        Chunk("material-icons", stub=True, css="body"),
        Chunk("roboto", stub=True, css="body"),
    ),
    # Vuetify (JS and CSS) is in the core bundle of the Vue 2 build
    False: (
        Chunk("katex", js=True, css="head"),
        Chunk("jupyter-css", stub=True, css="head"),
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


@dataclasses.dataclass(frozen=True)
class FrontendAssets:
    package: str
    version: str
    base: str
    core_js: str
    core_css: str
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
        name = css_file(chunk.name, ipywidgets_major)
        return CssLink(feature=chunk.name, url=base + name if chunk.name in enabled else None, data_href=name)

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
            names.append(css_file(chunk.name, ipywidgets_major))
    return names
