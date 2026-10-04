import importlib
import logging
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import List

import ipyvuetify as v
import ipywidgets as widgets
import pytest
from click.testing import CliRunner

import solara.__main__
import solara.server.app
import solara.server.settings
import solara.settings
from solara.components.markdown import _has_math
from solara.server import frontend, server
from solara.server.app import AppScript

HERE = Path(__file__).parent
# The page of Solara 1.63.1 (before --frontend), rendered with the page fixture below: page() on commit 369a9ad4.
GOLDEN_FULL = HERE / "golden" / "full_page.html"
NBEXTENSIONS = ["jupyter-vue/extension", "jupyter-vuetify/extension", "ipyaggrid/extension"]


def normalize(html: str) -> str:
    # embedded files: keep the path, drop the content (those files change on their own)
    html = re.sub(r"/\*\npath=([^\n]*)\n\*/.*?</(script|style)>", r"/*path=\1*/EMBEDDED</\2>", html, flags=re.S)
    html = re.sub(r"\?v=[0-9a-f]+", "?v=HASH", html)
    return html


@pytest.fixture
def page(no_kernel_context, tmp_path: Path, monkeypatch):
    """Render the page with a fixed environment, so the output does not depend on the machine."""
    app_file = tmp_path / "app.py"
    app_file.write_text("import solara\n\n\n@solara.component\ndef Page():\n    solara.Text('hi')\n")
    app_script = AppScript(str(app_file))
    monkeypatch.setitem(solara.server.app.apps, "__default__", app_script)
    monkeypatch.setattr(solara.server.settings.main, "mode", "production")
    # production would gc.freeze() the whole test process on the first app run
    monkeypatch.setattr(solara.server.settings.main, "gc_freeze", False)
    monkeypatch.setattr(solara.server.settings.assets, "fontawesome_enabled", True)
    monkeypatch.setattr(solara.settings.assets, "proxy", True)
    monkeypatch.setattr(server, "vue3", True)
    monkeypatch.setattr(server, "ipywidgets_major", 8)
    monkeypatch.setattr(server, "get_nbextensions", lambda: (NBEXTENSIONS, {name: f"hash-{name.split('/')[0]}" for name in NBEXTENSIONS}))
    monkeypatch.setattr(solara.server.app, "client_version", lambda: "CLIENT_VERSION")
    try:
        esm = importlib.import_module("solara.server.esm")
        monkeypatch.setattr(esm, "get_module_urls", lambda: [])
    except ModuleNotFoundError:
        pass

    def render(**kwargs) -> str:
        html = server.read_root("/", **kwargs)
        assert html is not None
        return normalize(html)

    try:
        yield render
    finally:
        app_script.close()


@pytest.fixture(autouse=True)
def fresh_frontend(monkeypatch):
    # warnings are once per process; the py3.8 lane runs Vue 2, these tests are about Vue 3 unless they say otherwise
    monkeypatch.setattr(frontend, "_warned", set())
    monkeypatch.setattr(frontend, "vue3", True)
    yield


def test_parse_presets():
    assert frontend.parse("full").features == frozenset(frontend.FEATURES)
    assert frontend.parse("").features == frozenset(frontend.FEATURES)
    assert frontend.parse("minimal").features == frozenset()
    assert frontend.parse(" Minimal , +Katex ").spec == "minimal,+katex"
    assert frontend.parse("minimal,+katex").features == {"katex"}
    assert frontend.parse("full,-mermaid").features == frozenset(frontend.FEATURES) - {"mermaid"}
    # without a preset, full is the start
    assert frontend.parse("-mermaid").spec == "full,-mermaid"
    # underscores are accepted
    assert "jupyter-controls" in frontend.parse("minimal,+jupyter_controls")


def test_parse_closure():
    # Vuetify's icons use mdi, its typography (e.g. caption font-weight-light) uses Roboto, and it needs its CSS
    assert frontend.parse("minimal,+vuetify").features == {"vuetify", "mdi", "roboto", "vuetify-css"}
    assert frontend.parse("minimal,+jupyter-controls").features == {"jupyter-controls", "jupyter-css"}
    assert frontend.parse("minimal,+output-widget").features == {"output-widget", "jupyter-css"}
    # turning off what something else needs is an error, unless that is off too
    with pytest.raises(ValueError, match="'vuetify' needs 'mdi'"):
        frontend.parse("full,-mdi")
    assert "mdi" not in frontend.parse("full,-vuetify,-mdi")


@pytest.mark.parametrize("spec", ["full,-vuetify-css", "minimal,+vuetify,-vuetify-css", "minimal,-vuetify-css,+vuetify", "full,+vuetify-css,-vuetify-css"])
def test_parse_vuetify_css_opt_out(spec):
    # Vuetify's CSS comes with vuetify, but an app that ships its own Vuetify CSS leaves it out: the last + or - wins
    parsed = frontend.parse(spec)
    assert "vuetify" in parsed and "mdi" in parsed and "roboto" in parsed
    assert "vuetify-css" not in parsed
    assert parsed.off == {"vuetify-css"}
    # the suggested value keeps the opt-out
    assert "vuetify-css" not in frontend.parse(parsed.suggest("katex"))
    # +vuetify-css after -vuetify-css turns it on again
    assert "vuetify-css" in frontend.parse(spec + ",+vuetify-css")


def test_parse_vuetify_css_follows_vuetify():
    # the full preset has Vuetify's CSS because it has Vuetify: a page without Vuetify gets no Vuetify CSS, as before
    assert "vuetify-css" in frontend.parse("full")
    assert "vuetify-css" not in frontend.parse("full,-vuetify")
    assert "vuetify-css" not in frontend.parse("minimal")
    # an app can still ask for it, e.g. for Vuetify that loads on first use
    assert frontend.parse("minimal,+vuetify-css").features == {"vuetify-css"}


@pytest.mark.parametrize("spec", ["full,-roboto", "minimal,+vuetify,-roboto", "minimal,-roboto,+vuetify", "full,+roboto,-roboto"])
def test_parse_roboto_opt_out(spec):
    # Roboto comes with vuetify, but an app with its own font leaves it out: the last +roboto or -roboto wins
    parsed = frontend.parse(spec)
    assert "vuetify" in parsed and "mdi" in parsed
    assert "roboto" not in parsed
    assert parsed.off == {"roboto"}
    # the suggested value keeps the opt-out
    assert "roboto" not in frontend.parse(parsed.suggest("katex"))
    # +roboto after -roboto turns it on again
    assert "roboto" in frontend.parse(spec + ",+roboto")


def test_parse_suggests_a_value_that_works():
    # both jupyter-controls and output-widget need jupyter-css: the suggestion turns off both
    with pytest.raises(ValueError) as error:
        frontend.parse("full,-jupyter-css")
    message = str(error.value)
    assert "'jupyter-controls' and 'output-widget' need 'jupyter-css'" in message
    suggestion = re.search(r"\('(-[^']*)'\)", message)
    assert suggestion is not None and suggestion.group(1) == "-jupyter-controls,-output-widget,-jupyter-css"
    assert "jupyter-css" not in frontend.parse("full," + suggestion.group(1))


def test_from_page():
    # what the page sends with run (window.solaraFrontend)
    page = frontend.from_page({"spec": "minimal,+katex", "features": ["katex", "no-such-feature"], "chunks": ["katex"]})
    assert page == frontend.Frontend(spec="minimal,+katex", features=frozenset({"katex"}))
    # an older page, or a value that is not a page's: the server setting applies
    assert frontend.from_page(None) is None
    assert frontend.from_page({"spec": "minimal", "features": "katex"}) is None
    # the spec shows up in the server log, so it must be a valid setting
    assert frontend.from_page({"spec": "minimal\nERROR: fake log line", "features": []}) is None
    # a valid setting that is longer than any page sends, or more features than exist
    assert frontend.from_page({"spec": "full" + ",+katex" * 1000, "features": []}) is None
    assert frontend.from_page({"spec": "full", "features": ["katex"] * 100}) is None


def test_logger_level_from_logging_config_stays():
    # solara run --log-level configures logging before the server process imports solara.server.frontend
    code = (
        "import logging; logging.getLogger('solara.server.frontend').setLevel(logging.ERROR); "
        "import solara.server.frontend; print(logging.getLogger('solara.server.frontend').level)"
    )
    output = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True, timeout=60).stdout
    assert output.strip().splitlines()[-1] == str(logging.ERROR)


@pytest.mark.parametrize(
    "value, message",
    [
        ("minimum", "Did you mean 'minimal'"),
        ("minimal,+kattex", "Did you mean 'katex'"),
        ("minimal,katex", "write '\\+katex'"),
        ("full,minimal", "must come first"),
        ("katex", "write '\\+katex'"),
        ("minimal,+full", "the preset 'full' must come first"),
    ],
)
def test_parse_errors(value, message):
    with pytest.raises(ValueError, match=message):
        frontend.parse(value)


def test_effective_vue2_forces_vuetify(caplog):
    minimal = frontend.parse("minimal")
    assert frontend.effective(minimal, vue3=True).features == frozenset()
    with caplog.at_level(logging.WARNING, logger="solara.server.frontend"):
        vue2 = frontend.effective(minimal, vue3=False)
    # the Vue 2 build has Vuetify in its core bundle, so it keeps what Vuetify needs (mdi), and Roboto and Vuetify's CSS
    # come with it
    assert vue2.features == {"vuetify", "mdi", "roboto", "vuetify-css"}
    assert "The Vue 2 build cannot leave out mdi, vuetify, so they stay on." in caplog.text
    # Vuetify's CSS is a file of its own on Vue 2 too: an app with its own Vuetify CSS leaves it out, without a warning
    caplog.clear()
    for spec in ["full,-vuetify-css", "minimal,+vuetify,-vuetify-css"]:
        with caplog.at_level(logging.WARNING, logger="solara.server.frontend"):
            vue2 = frontend.effective(frontend.parse(spec), vue3=False)
        assert "vuetify" in vue2 and "mdi" in vue2 and "roboto" in vue2
        assert "vuetify-css" not in vue2
    assert "cannot leave out" not in caplog.text
    assert "vuetify-css" not in frontend.effective(frontend.parse("minimal,-vuetify-css"), vue3=False)
    # a Vue 2 page without +vuetify still has Vuetify, so its CSS too
    assert "vuetify-css" in frontend.effective(frontend.parse("full,-vuetify"), vue3=False)
    # an app with its own font leaves Roboto out, also when the Vue 2 build forces Vuetify on
    for spec in ["minimal,-roboto", "full,-roboto", "minimal,+vuetify,-roboto"]:
        vue2 = frontend.effective(frontend.parse(spec), vue3=False)
        assert "vuetify" in vue2 and "mdi" in vue2
        assert "roboto" not in vue2
    # vue-sfc does not exist on Vue 2
    assert "vue-sfc" not in frontend.effective(frontend.parse("full"), vue3=False)


@pytest.mark.parametrize("vue3", [True, False])
def test_effective_font_awesome_alias(vue3):
    # SOLARA_ASSETS_FONTAWESOME_ENABLED=false keeps working, on Vue 2 and Vue 3
    assert "font-awesome" not in frontend.effective(frontend.parse("full"), vue3=vue3, fontawesome_enabled=False)
    assert "font-awesome" in frontend.effective(frontend.parse("full"), vue3=vue3, fontawesome_enabled=True)


def test_current_reads_settings(monkeypatch):
    monkeypatch.setattr(solara.server.settings.main, "frontend", "minimal,+katex")
    assert frontend.current().features == {"katex"}
    monkeypatch.setattr(solara.server.settings.main, "frontend", "full")
    assert frontend.current().features == frozenset(frontend.FEATURES)


def test_vuetify_enabled(monkeypatch, no_kernel_context):
    monkeypatch.setattr(solara.server.settings.main, "frontend", "minimal")
    # outside a virtual kernel (Jupyter) it is always on
    assert frontend.vuetify_enabled()


def test_vuetify_enabled_in_kernel(monkeypatch):
    monkeypatch.setattr(solara.server.settings.main, "frontend", "minimal")
    assert not frontend.vuetify_enabled()
    monkeypatch.setattr(solara.server.settings.main, "frontend", "minimal,+vuetify")
    assert frontend.vuetify_enabled()


def test_warning_once_per_feature(monkeypatch, caplog):
    monkeypatch.setattr(solara.server.settings.main, "frontend", "minimal,+katex")
    with caplog.at_level(logging.WARNING, logger="solara.server.frontend"):
        v.Btn()
        v.Btn()
        widgets.IntSlider()
        frontend.check_widget(v.Btn())
        frontend.check_widget(v.Btn())
        frontend.check_widget(widgets.IntSlider())
        frontend.log_lazy_load("vuetify")
    messages = [record.getMessage() for record in caplog.records if record.name == "solara.server.frontend"]
    assert len(messages) == 2
    assert "'vuetify'" in messages[0] and "--frontend=minimal,+katex,+vuetify" in messages[0]
    assert "'jupyter-controls'" in messages[1]


def test_no_warning_outside_kernel(monkeypatch, caplog, no_kernel_context):
    monkeypatch.setattr(solara.server.settings.main, "frontend", "minimal")
    with caplog.at_level(logging.WARNING, logger="solara.server.frontend"):
        frontend.warn_missing("katex", "solara.Markdown")
    assert not [record for record in caplog.records if record.name == "solara.server.frontend"]


def test_markdown_warns_for_math(monkeypatch, caplog):
    from solara.components.markdown import _markdown_template

    monkeypatch.setattr(solara.server.settings.main, "frontend", "minimal")
    with caplog.at_level(logging.WARNING, logger="solara.server.frontend"):
        template = _markdown_template("<p>no math</p>")
        assert "const hasMath = false" in template
        # a single $, or $ in code, is no math: KaTeX's auto-render skips code, and needs a closing delimiter
        template = _markdown_template('<div class="highlight"><pre><span></span><code>$ pip install solara\n</code></pre></div>')
        assert "const hasMath = false" in template
        template = _markdown_template("<p>Price ($)</p><p>Total: $1,234</p><p><code>$x$</code></p>")
        assert "const hasMath = false" in template
        template = _markdown_template("<p>$x^2$</p>")
        assert "const hasMath = true" in template
        for html in ["<p>$$\nx\n$$</p>", "<p>\\(x\\)</p>", "<p>\\[x\\]</p>", "<p>from $5 to $10</p>"]:
            assert "const hasMath = true" in _markdown_template(html), html
        # the template compiler of Vue decodes character references before KaTeX sees the text
        for html in ["<p>&#36;x+3&#36;</p>", "<p>&dollar;x&dollar;</p>", "<p>&#92;(x&#92;)</p>"]:
            assert "const hasMath = true" in _markdown_template(html), html
        for html in ["<p>&amp;#36;x&amp;#36;</p>", "<p>a &amp; b</p>", "<p><code>&#36;x&#36;</code></p>"]:
            assert "const hasMath = false" in _markdown_template(html), html
    messages = [record.getMessage() for record in caplog.records if record.name == "solara.server.frontend"]
    assert len(messages) == 1 and "'katex'" in messages[0]


@pytest.mark.parametrize(
    "unit",
    [
        "x \\( ",  # an unclosed \( in each part
        "<code> ",  # an unclosed <code> in each part
        "&#92;( ",
        "< ",
    ],
)
def test_has_math_takes_linear_time(unit):
    # Markdown can come from users (e.g. a chat app): the check must not stall the server
    text = "$ " + unit * 20_000
    start = time.perf_counter()
    assert not _has_math(text)
    # a quadratic check takes 5 seconds or more here, a linear one a few milliseconds
    assert time.perf_counter() - start < 1


def test_cli_rejects_bad_frontend(monkeypatch):
    def fail():
        raise AssertionError("the frontend check must run before the version check")

    monkeypatch.setattr(solara.__main__, "_check_version", fail)
    result = CliRunner().invoke(solara.__main__.cli, ["run", "app.py", "--frontend", "minimum"])
    assert result.exit_code == 2
    assert "--frontend" in result.output
    assert "minimal" in result.output


# the parts of the page that the frontend features add (or change), in a page normalized by normalize()
FEATURE_PARTS = [
    r'<link rel="preload" as="script" href="[^"]*">',
    r'<link href="[^"]*/main8\.[a-z-]+\.css"[^>]*></link>',
    r'<template data-solara-css-slot="[a-z-]+"></template>',
    r'<script src="[^"]*/solara-vuetify-app8\.[a-z-]+\.min\.js" onerror="event\.target\.remove\(\)"></script>',
    r"<script>\s*window\.solaraFrontend = .*?</script>",
    r"<script>\s*// run the chunks of the preloaded features.*?</script>",
    r"// the AMD modules of the bundle.*?defineAppAmdModules\(\);",
]
# the widget manager waits for the nbextensions (solara.nbextensionsLoaded): removing these parts gives the old requirejs([...]);
NBEXTENSIONS_LOADED = [
    r"// an nbextension configures requirejs.*?of such a widget",
    r"solara\.nbextensionsLoaded = new Promise\(\(resolve\) => ",
    r", \(\) => resolve\(\), \(error\) => \{\s*console\.error\(error\);\s*resolve\(\);\s*\}\)",
]
LOCAL_REQUIREJS = r'<script src="/static/require\.min\.js\?v=HASH"></script>'
CDN_REQUIREJS = r'<script src="/_solara/cdn/requirejs@2\.3\.6/require\.js" crossorigin="anonymous">\s*</script>'
# the fonts moved into the mdi, material-icons and roboto CSS chunks
FONTS_CSS = r'<link href="[^"]*/fonts\.css" rel="stylesheet"></link>'


def _lines(html: str, remove: List[str]) -> List[str]:
    for pattern in remove:
        html = re.sub(pattern, "", html, flags=re.S)
    # the package versions change with each release
    html = re.sub(r"(@widgetti/solara-vuetify3?-app)@[0-9.]+/", r"\1@VERSION/", html)
    lines = [line.strip() for line in html.splitlines()]
    return [line for line in lines if line]


def test_full_page_unchanged(page):
    golden = GOLDEN_FULL.read_text(encoding="utf-8")
    html = page()
    assert len(re.findall(r'<link rel="preload" as="script"', html)) == 2
    assert re.search(LOCAL_REQUIREJS, html)
    assert _lines(html, FEATURE_PARTS + NBEXTENSIONS_LOADED + [LOCAL_REQUIREJS]) == _lines(golden, [FONTS_CSS, CDN_REQUIREJS])


@pytest.mark.parametrize("vue3", [True, False])
def test_legacy_page(page, monkeypatch, vue3):
    # The Jupyter popout and pyodide pages. The published core bundle has no Vuetify, KaTeX or widget CSS
    # any more, so these pages need the chunks of the full page too. They have no preloads, and load
    # require.js from the CDN (the Jupyter server extension only serves /solara/static/assets/*).
    monkeypatch.setattr(server, "vue3", vue3)
    html = page(legacy=True)
    assert 'rel="preload"' not in html
    assert re.search(CDN_REQUIREJS, html)
    assert not re.search(LOCAL_REQUIREJS, html)
    chunks = ["vuetify", "katex", "sanitizer", "jupyter-controls", "output-widget"] if vue3 else ["katex", "sanitizer", "jupyter-controls", "output-widget"]
    scripts = re.findall(r'<script src="[^"]*/solara-vuetify-app8(\.[a-z-]+)?\.min\.js"(?: onerror="event\.target\.remove\(\)")?></script>', html)
    assert scripts == ["", *(f".{chunk}" for chunk in chunks)]
    # Vuetify's CSS (main8.vuetify.css) is the first chunk CSS: on Vue 2 before the core CSS, on Vue 3 after it
    css = ["vuetify", "katex", "jupyter-css", "mdi", "material-icons", "roboto"]
    assert re.findall(r'<link href="[^"]*/main8\.([a-z-]+)\.css"[^>]*data-href="main8\.\1\.css"', html) == css
    assert '"spec": "full"' in html
    assert "solara.setEnabledFeatures(solaraFrontend.features);" in html
    assert "solara.loadPreloadedFeaturesSync()" in html
    if vue3:
        # apart from the feature parts, the page is the one of Solara 1.63.1
        golden = GOLDEN_FULL.read_text(encoding="utf-8")
        assert _lines(html, FEATURE_PARTS + NBEXTENSIONS_LOADED) == _lines(golden, [FONTS_CSS])


def test_full_page_vue_sfc_preload(page, monkeypatch, tmp_path):
    (tmp_path / "jupyter-vue").mkdir()
    (tmp_path / "jupyter-vue" / "nodeps-vue-sfc.js").write_text("")
    monkeypatch.setattr(server, "nbextension_root", lambda name: tmp_path / "jupyter-vue")
    html = page()
    assert '<script defer src="/jupyter/nbextensions/jupyter-vue/nodeps-vue-sfc.js?hash-jupyter-vue"' in html
    # a failed preload tag must go, so webpack makes a fresh one when the compiler is needed
    assert 'data-webpack="jupyter-vue-nodeps:chunk-vue-sfc" onerror="event.target.remove()"></script>' in html
    assert "nodeps-vue-sfc.js" not in page(frontend="full,-vue-sfc")


def test_minimal_page(page):
    html = page(frontend="minimal")
    assert "<v-app" not in html
    assert "v-application" not in html
    assert "pre-render-theme" not in html
    assert '<div id="app" class="solara-app">' in html
    assert 'class="solara-shell"' in html
    assert "/static/solara-vue.css" in html
    assert "jupyter-vuetify/nodeps.js" not in html
    assert "jupyter-vue/nodeps.js" in html
    assert "font-awesome" not in html
    assert "fonts.css" not in html
    assert re.search(r'window\.solaraFrontend = \{"chunks": \[\], "features": \[\], "spec": "minimal"\}', html)
    # no chunk is preloaded, but every feature has a slot for its CSS
    assert not re.search(r"solara-vuetify-app8\.[a-z-]+\.min\.js", html)
    for feature in ["vuetify", "katex", "jupyter-css", "mdi", "material-icons", "roboto"]:
        assert f'<template data-solara-css-slot="{feature}"></template>' in html


@pytest.mark.parametrize("vue3", [True, False])
def test_vuetify_page_has_roboto(page, monkeypatch, vue3):
    # Vuetify's typography (e.g. "caption font-weight-light") uses Roboto: a page with Vuetify preloads the Roboto CSS
    monkeypatch.setattr(server, "vue3", vue3)
    roboto = r'<link href="[^"]*/main8\.roboto\.css" rel="stylesheet" data-href="main8\.roboto\.css"'
    # full, as before
    assert len(re.findall(roboto, page())) == 1
    # Vue 2 always has Vuetify (also in minimal), Vue 3 with +vuetify
    for spec in ["minimal,+vuetify"] + ([] if vue3 else ["minimal"]):
        html = page(frontend=spec)
        assert len(re.findall(roboto, html)) == 1
        assert re.search(r'window\.solaraFrontend = \{[^\n]*"features": \[[^\]]*"roboto"', html)
    # without Vuetify (Vue 3 minimal) or with -roboto (an app with its own font), the page has no Roboto link: only
    # the slot, where Vuetify that loads on first use puts it, unless the spec says -roboto
    for spec in (["minimal"] if vue3 else []) + ["full,-roboto", "minimal,-roboto", "minimal,+vuetify,-roboto"]:
        html = page(frontend=spec)
        assert not re.search(roboto, html)
        assert '<template data-solara-css-slot="roboto"></template>' in html
        assert re.search(r'window\.solaraFrontend = \{[^\n]*"spec": "' + re.escape(spec) + '"', html)


VUETIFY_CSS = r'<link href="[^"]*/main8\.vuetify\.css" rel="stylesheet" class="solara-template-css" data-href="main8\.vuetify\.css"></link>'
CORE_CSS = r'<link href="[^"]*/main8\.css" rel="stylesheet" class="solara-template-css"></link>'


@pytest.mark.parametrize("vue3", [True, False])
def test_vuetify_css(page, monkeypatch, vue3):
    # Vuetify's CSS comes with Vuetify, at the place it had before it was a feature of its own: on Vue 3 the CSS of the
    # vuetify chunk, right after the core CSS; on Vue 2 the start of the core CSS (main8.css), so right before it
    monkeypatch.setattr(server, "vue3", vue3)
    for spec in ["full", "minimal,+vuetify"] + ([] if vue3 else ["minimal"]):
        html = page(frontend=spec)
        assert len(re.findall(VUETIFY_CSS, html)) == 1
        # the slot (for a lazy load) is right after the link
        vuetify_css = VUETIFY_CSS + r'\s*<template data-solara-css-slot="vuetify"></template>'
        assert re.search(CORE_CSS + r"\s*" + vuetify_css if vue3 else vuetify_css + r"\s*" + CORE_CSS, html), spec
        assert re.search(r'window\.solaraFrontend = \{[^\n]*"features": \[[^\]]*"vuetify-css"', html)
    # an app with its own Vuetify CSS (-vuetify-css), or a page without Vuetify (Vue 3): no link, only the slot (on Vue 3
    # Vuetify that loads on first use puts its CSS there, unless the spec says -vuetify-css)
    for spec in ["full,-vuetify-css", "minimal,-vuetify-css", "minimal,+vuetify,-vuetify-css"] + (["minimal", "full,-vuetify"] if vue3 else []):
        html = page(frontend=spec)
        assert "main8.vuetify.css" not in html, spec
        assert html.count('<template data-solara-css-slot="vuetify"></template>') == 1
        assert not re.search(r'window\.solaraFrontend = \{[^\n]*"vuetify-css"', html)
        # the rest of the page keeps Vuetify, if it has it (always on Vue 2)
        assert ("<v-app" in html) == ("vuetify" in frontend.effective(frontend.parse(spec), vue3=vue3)), spec


def test_chunk_scripts_removed_on_error(page):
    # with the CDN proxy off the src is absolute, and webpack would wait for a failed tag with the same src
    tags = re.findall(r'<script src="[^"]*/solara-vuetify-app8\.[a-z-]+\.min\.js"[^>]*>', page())
    assert len(tags) == 5
    assert all('onerror="event.target.remove()"' in tag for tag in tags)


def test_minimal_page_has_no_dark_mode(page):
    # the shell without Vuetify has a white page: never load the dark Jupyter theme (white text) there
    no_dark = re.compile(r"function inDarkMode\(\) \{\s*//[^\n]*\s*return false;")
    assert no_dark.search(page(frontend="minimal"))
    assert not no_dark.search(page())


def test_minimal_page_plus_katex(page):
    html = page(frontend="minimal,+katex")
    assert "solara-vuetify-app8.katex.min.js" in html
    assert 'data-href="main8.katex.css"' in html
    assert "solara-vuetify-app8.vuetify.min.js" not in html
