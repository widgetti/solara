import re
import sys
from pathlib import Path

import pytest

from solara.server import frontend, frontend_assets

HERE = Path(__file__).parent
PACKAGE_DIRS = {True: "solara-vuetify3-app", False: "solara-vuetify-app"}
CDN = "/_solara/cdn"


@pytest.mark.parametrize("vue3", [True, False])
@pytest.mark.parametrize("ipywidgets_major", [7, 8])
@pytest.mark.parametrize("production", [True, False])
def test_asset_urls(vue3, ipywidgets_major, production):
    package, version = frontend_assets.PACKAGES[vue3]
    base = f"{CDN}/{package}@{version}/dist/"
    suffix = ".min.js" if production else ".js"
    full = frontend.effective(frontend.parse("full"), vue3=vue3)
    assets = frontend_assets.page_assets(vue3, ipywidgets_major, production, CDN, full)
    assert assets.core_js == f"{base}solara-vuetify-app{ipywidgets_major}{suffix}"
    # CSS does not depend on production
    assert assets.core_css == f"{base}main{ipywidgets_major}.css"
    for css in assets.head_first_css + assets.head_css + assets.body_css:
        assert css.url == f"{base}main{ipywidgets_major}.{css.slot}.css"
        assert css.data_href == f"main{ipywidgets_major}.{css.slot}.css"
        # Vuetify's CSS keeps its file name (and slot), main{M}.vuetify.css
        assert css.slot == ("vuetify" if css.feature == "vuetify-css" else css.feature)
    # Vuetify's CSS has the place it had: on Vue 3 the CSS of the vuetify chunk (after the core CSS), on Vue 2 the start
    # of the core CSS (before it)
    assert [css.feature for css in assets.head_first_css] == ([] if vue3 else ["vuetify-css"])
    assert [css.feature for css in assets.head_css] == (["vuetify-css"] if vue3 else []) + ["katex", "jupyter-css"]
    assert [css.feature for css in assets.body_css] == ["mdi", "material-icons", "roboto"]
    expected_chunks = (["vuetify"] if vue3 else []) + ["katex", "jquery", "lumino", "sanitizer", "jupyter-controls", "output-widget"]
    assert assets.chunk_names == expected_chunks
    assert assets.chunk_js == [f"{base}solara-vuetify-app{ipywidgets_major}.{name}{suffix}" for name in expected_chunks]

    minimal = frontend.effective(frontend.parse("minimal"), vue3=vue3)
    assets = frontend_assets.page_assets(vue3, ipywidgets_major, production, CDN, minimal)
    # Vuetify is always on: on Vue 2 it is in the core bundle, on Vue 3 a chunk
    assert assets.chunk_names == (["vuetify"] if vue3 else [])
    # Vuetify brings mdi, and roboto and Vuetify's CSS come with it; the rest is not preloaded: only the slot, so a lazy load
    # puts the CSS in the same place
    linked = [css.feature for css in assets.head_first_css + assets.head_css + assets.body_css if css.url]
    assert linked == ["vuetify-css", "mdi", "roboto"]

    controls = frontend.effective(frontend.parse("minimal,+jupyter-controls"), vue3=vue3)
    assets = frontend_assets.page_assets(vue3, ipywidgets_major, production, CDN, controls)
    # the controls use jQuery and Lumino of the jquery and lumino chunks, which run before them
    assert assets.chunk_names == (["vuetify"] if vue3 else []) + ["jquery", "lumino", "sanitizer", "jupyter-controls"]
    assert [css.feature for css in assets.head_css if css.url] == (["vuetify-css"] if vue3 else []) + ["jupyter-css"]

    # Vuetify's icons need the mdi font, and the Roboto font and Vuetify's CSS come with it
    vuetify = frontend.effective(frontend.parse("minimal,+vuetify"), vue3=vue3)
    assets = frontend_assets.page_assets(vue3, ipywidgets_major, production, CDN, vuetify)
    assert [css.feature for css in assets.body_css if css.url] == ["mdi", "roboto"]
    assert [css.feature for css in assets.head_first_css + assets.head_css if css.url] == ["vuetify-css"]
    # unless the app uses its own font
    for spec in ["minimal,+vuetify,-roboto", "full,-roboto"]:
        own_font = frontend.effective(frontend.parse(spec), vue3=vue3)
        assets = frontend_assets.page_assets(vue3, ipywidgets_major, production, CDN, own_font)
        assert [css.feature for css in assets.body_css if css.url] == ["mdi"] + (["material-icons"] if spec == "full,-roboto" else [])
    # unless the app ships its own Vuetify CSS: no link, only the slot
    for spec in ["full,-vuetify-css", "minimal,+vuetify,-vuetify-css", "minimal,-vuetify-css"]:
        own_css = frontend.effective(frontend.parse(spec), vue3=vue3)
        assets = frontend_assets.page_assets(vue3, ipywidgets_major, production, CDN, own_css)
        vuetify_css = [css for css in assets.head_first_css + assets.head_css if css.feature == "vuetify-css"]
        assert [(css.url, css.slot) for css in vuetify_css] == [(None, "vuetify")]
        # the fonts stay
        fonts = {
            "full,-vuetify-css": ["mdi", "material-icons", "roboto"],
            "minimal,+vuetify,-vuetify-css": ["mdi", "roboto"],
            "minimal,-vuetify-css": ["mdi", "roboto"],
        }
        assert [css.feature for css in assets.body_css if css.url] == fonts[spec], spec
        # Vuetify itself stays
        assert ("vuetify" in assets.chunk_names) == vue3


def _dist(vue3: bool):
    package, version = frontend_assets.PACKAGES[vue3]
    candidates = [
        # devlinked (npm run devlink)
        Path(sys.prefix) / "share" / "solara" / "cdn" / f"{package}@{version}" / "dist",
        # a build in the repo
        HERE.parent.parent / "packages" / PACKAGE_DIRS[vue3] / "dist",
    ]
    for dist in candidates:
        # skip a build from before the feature chunks (or a proxy cache of one)
        if (dist / frontend_assets.css_file("katex", 8)).exists():
            return dist
    pytest.skip(f"no build of {package}@{version} with feature chunks")


@pytest.mark.parametrize("vue3", [True, False])
def test_assets_match_dist(vue3):
    dist = _dist(vue3)
    expected = set()
    for ipywidgets_major in [7, 8]:
        for production in [True, False]:
            names = frontend_assets.dist_files(vue3, ipywidgets_major, production)
            for name in names:
                assert (dist / name).exists(), f"{name} is not in {dist}"
            expected.update(names)
            full = frontend.effective(frontend.parse("full"), vue3=vue3)
            assets = frontend_assets.page_assets(vue3, ipywidgets_major, production, "", full)
            for css in assets.head_first_css + assets.head_css + assets.body_css:
                assert (dist / css.data_href).exists()
    built = {path.name for path in dist.iterdir() if path.suffix in (".js", ".css")}
    assert built == expected, f"files in {dist} that the server does not know about: {sorted(built - expected)}"


@pytest.mark.parametrize("ipywidgets_major", [7, 8])
def test_vuetify_css_keeps_v_main_longhands(ipywidgets_major):
    # the minifier must not merge Vuetify's .v-main padding longhands into the earlier shorthand: with an
    # invalid --v-layout-left (a width="min-content" drawer) the shorthand is void, and padding-top would be 0
    dist = _dist(True)
    css = (dist / frontend_assets.css_file("vuetify", ipywidgets_major)).read_text(encoding="utf8")
    rules = re.findall(r"(?:^|})\.v-main\{([^}]*)\}", css)
    padded = [rule for rule in rules if "padding" in rule]
    assert padded, "no .v-main padding rule"
    assert "padding-top:var(--v-layout-top)" in padded[-1]


@pytest.mark.parametrize("vue3", [True, False])
def test_sanitizer_postcss_as_before(vue3):
    # sanitize-html needs postcss to keep style attributes; the Vue 2 ipywidgets 8 production build had none (it drops them)
    dist = _dist(vue3)
    for ipywidgets_major in [7, 8]:
        for production in [True, False]:
            chunk = dist / f"solara-vuetify-app{ipywidgets_major}.sanitizer{'.min' if production else ''}.js"
            has_postcss = "CssSyntaxError" in chunk.read_text(encoding="utf8")
            assert has_postcss == (vue3 or ipywidgets_major == 7 or not production), chunk.name


@pytest.mark.parametrize("vue3", [True, False])
@pytest.mark.parametrize("ipywidgets_major", [7, 8])
@pytest.mark.parametrize("production", [True, False])
def test_core_umd_factory_in_parentheses(vue3, ipywidgets_major, production):
    # V8 compiles a function in parentheses eagerly, with the script (off the main thread in Chrome), and any other
    # function lazily on the main thread when it is called. The UMD wrapper calls its factory at once, so the factory
    # must be in parentheses, as in the published bundles: "}(self,(()=>" (production), "})(self, (() => {" (development).
    # terser >= 5.43 drops them unless format.wrap_func_args is on (webpack.config.js); WrapUmdFactoryPlugin adds them
    # to the development builds. Without them, the factory compile took 65-80 ms of main thread at 4x CPU.
    dist = _dist(vue3)
    head = (dist / frontend_assets.js_file("core", ipywidgets_major, production)).read_text(encoding="utf8")[:5000]
    if production:
        assert "}(self,(()=>(()=>{" in head
        assert "}(self,()=>" not in head
    else:
        assert re.search(r"^\}\)\(self, \(\(\) => \{$", head, re.M)
        assert not re.search(r"^\}\)\(self, \(\) => \{$", head, re.M)


# a CSS class that only the markdown renderer of @jupyterlab/rendermime adds
RENDERMIME_MARKER = "jp-RenderedMarkdown"


@pytest.mark.parametrize("vue3", [True, False])
@pytest.mark.parametrize("ipywidgets_major", [7, 8])
@pytest.mark.parametrize("production", [True, False])
def test_output_renderers_out_of_core(vue3, ipywidgets_major, production):
    # only the Output widget renders outputs: the renderers are in the output-widget chunk, and the core has a
    # RenderMimeRegistry stand-in (solara-widget-manager/src/rendermime.ts)
    dist = _dist(vue3)
    core = (dist / frontend_assets.js_file("core", ipywidgets_major, production)).read_text(encoding="utf8")
    output = (dist / frontend_assets.js_file("output-widget", ipywidgets_major, production)).read_text(encoding="utf8")
    assert RENDERMIME_MARKER not in core
    assert RENDERMIME_MARKER in output


# a string that only jQuery has (its selector engine), and a CSS class that only the Lumino DockPanel uses
JQUERY_MARKER = "Syntax error, unrecognized expression: "
LUMINO_DOCK_MARKER = "lm-DockPanel"


@pytest.mark.parametrize("vue3", [True, False])
@pytest.mark.parametrize("ipywidgets_major", [7, 8])
@pytest.mark.parametrize("production", [True, False])
def test_lumino_out_of_core(vue3, ipywidgets_major, production):
    # the Lumino widgets beyond Widget and Panel are in the lumino chunk, not in the core
    dist = _dist(vue3)
    core = (dist / frontend_assets.js_file("core", ipywidgets_major, production)).read_text(encoding="utf8")
    lumino = (dist / frontend_assets.js_file("lumino", ipywidgets_major, production)).read_text(encoding="utf8")
    assert LUMINO_DOCK_MARKER not in core
    assert LUMINO_DOCK_MARKER in lumino


@pytest.mark.parametrize("vue3", [True, False])
@pytest.mark.parametrize("ipywidgets_major", [7, 8])
@pytest.mark.parametrize("production", [True, False])
def test_jquery_out_of_core(vue3, ipywidgets_major, production):
    # jQuery is only in the jquery chunk; the core has the stand-in that every 'jquery' import gets
    # (solara-widget-manager/src/jquery.ts), also the imports of the controls and the Output widget
    dist = _dist(vue3)

    def read(feature: str) -> str:
        return (dist / frontend_assets.js_file(feature, ipywidgets_major, production)).read_text(encoding="utf8")

    core = read("core")
    assert JQUERY_MARKER not in core
    assert "this widget uses jQuery" in core
    assert JQUERY_MARKER in read("jquery")
    for feature in ["lumino", "jupyter-controls", "output-widget"]:
        assert JQUERY_MARKER not in read(feature), feature


@pytest.mark.parametrize("ipywidgets_major", [7, 8])
@pytest.mark.parametrize("production", [True, False])
def test_vue3_feature_flags_defined(ipywidgets_major, production):
    # webpack defines two of Vue's esm-bundler feature flags (solara-vuetify3-app/webpack.config.js), so the core has
    # no runtime checks for them, and terser drops the code they turn off; __VUE_PROD_DEVTOOLS__ stays a runtime global
    dist = _dist(True)
    core = (dist / frontend_assets.js_file("core", ipywidgets_major, production)).read_text(encoding="utf8")
    assert "__VUE_OPTIONS_API__" not in core
    assert "__VUE_PROD_HYDRATION_MISMATCH_DETAILS__" not in core
    assert "__VUE_PROD_DEVTOOLS__" in core
