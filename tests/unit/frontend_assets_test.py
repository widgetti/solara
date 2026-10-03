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
    for css in assets.head_css + assets.body_css:
        assert css.url == f"{base}main{ipywidgets_major}.{css.feature}.css"
        assert css.data_href == f"main{ipywidgets_major}.{css.feature}.css"
    assert [css.feature for css in assets.head_css] == (["vuetify"] if vue3 else []) + ["katex", "jupyter-css"]
    assert [css.feature for css in assets.body_css] == ["mdi", "material-icons", "roboto"]
    expected_chunks = (["vuetify"] if vue3 else []) + ["katex", "sanitizer", "jupyter-controls", "output-widget"]
    assert assets.chunk_names == expected_chunks
    assert assets.chunk_js == [f"{base}solara-vuetify-app{ipywidgets_major}.{name}{suffix}" for name in expected_chunks]

    minimal = frontend.effective(frontend.parse("minimal"), vue3=vue3)
    assets = frontend_assets.page_assets(vue3, ipywidgets_major, production, CDN, minimal)
    # on Vue 2 vuetify is in the core bundle
    assert assets.chunk_js == []
    # not preloaded: only the slot, so a lazy load puts the CSS in the same place (Vue 2 always has Vuetify, so mdi, and roboto
    # comes with it)
    assert [css.feature for css in assets.head_css + assets.body_css if css.url] == ([] if vue3 else ["mdi", "roboto"])

    controls = frontend.effective(frontend.parse("minimal,+jupyter-controls"), vue3=vue3)
    assets = frontend_assets.page_assets(vue3, ipywidgets_major, production, CDN, controls)
    assert assets.chunk_names == ["sanitizer", "jupyter-controls"]
    assert [css.feature for css in assets.head_css if css.url] == ["jupyter-css"]

    # Vuetify's icons need the mdi font, and the Roboto font comes with it
    vuetify = frontend.effective(frontend.parse("minimal,+vuetify"), vue3=vue3)
    assets = frontend_assets.page_assets(vue3, ipywidgets_major, production, CDN, vuetify)
    assert [css.feature for css in assets.body_css if css.url] == ["mdi", "roboto"]
    # unless the app uses its own font
    for spec in ["minimal,+vuetify,-roboto", "full,-roboto"]:
        own_font = frontend.effective(frontend.parse(spec), vue3=vue3)
        assets = frontend_assets.page_assets(vue3, ipywidgets_major, production, CDN, own_font)
        assert [css.feature for css in assets.body_css if css.url] == ["mdi"] + (["material-icons"] if spec == "full,-roboto" else [])


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
            for css in assets.head_css + assets.body_css:
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
