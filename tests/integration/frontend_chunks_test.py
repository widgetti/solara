"""The frontend features (--frontend) in a browser: what the page preloads, and what it loads on first use."""

import logging
import re
from collections import Counter
from pathlib import Path
from typing import Dict, List

import ipywidgets
import playwright.sync_api
import pytest
import reacton.core

import solara
import solara.components.misc
import solara.server.server
import solara.server.settings
from solara.server import frontend, frontend_assets

HERE = Path(__file__).parent
# the vuetify3 lane: the Vue 2 build keeps Vuetify in its core bundle, so it cannot leave it out
vue3 = frontend.vue3
ipywidgets_major = int(ipywidgets.__version__.split(".")[0])

# a JS chunk of the app bundle, e.g. .../solara-vuetify3-app@5.2.0/dist/solara-vuetify-app8.katex.js
CHUNK_RE = re.compile(r"/@widgetti/solara-vuetify3?-app@[^/]+/dist/solara-vuetify-app\d\.([a-z-]+)(?:\.min)?\.js")
# the console warning of a lazy load (solara-widget-manager features.ts)
LAZY_RE = re.compile(r'Add "\+([a-z-]+)" to --frontend')
WEBSOCKET_CLOSED_RE = re.compile(r"WebSocket connection to .* failed: Invalid frame header")


@solara.component
def Hello():
    solara.Text("hello frontend")


@solara.component
def Slider():
    ipywidgets.IntSlider.element(description="chunk slider", value=3)


@solara.component
def MarkdownPlain():
    solara.Markdown("plain markdown text")


@solara.component
def MarkdownMath():
    solara.Markdown("math markdown: $E = mc^2$")


@solara.component
def TwoTexts():
    solara.Text("first fragment text")
    solara.Text("second fragment text")


@solara.component
def MarkdownSqrt():
    solara.Markdown(r"root markdown: $\sqrt{x}$")


@solara.component
def DisplayOutputs():
    import IPython.display

    # text/markdown in an Output widget: the markdown renderer of @jupyterlab/rendermime (it uses CodeMirror)
    solara.display(IPython.display.Markdown("first **md-bold-one**"))
    solara.display(IPython.display.Markdown("second **md-bold-two**\n\n```python\nx = 1\n```"))
    if ipywidgets_major >= 8:
        # the sanitizer keeps style attributes (sanitize-html needs postcss for that); the tests run in development
        # mode: as before, the Vue 2 ipywidgets 8 production build has no postcss, so it drops them
        solara.display(ipywidgets.Checkbox(description='<b style="color: rgb(0, 128, 0)">green desc</b>', description_allow_html=True))


@solara.component
def SidebarApp():
    # the default layout (AppLayout) gets a drawer of width="min-content", so Vuetify 3 sets --v-layout-left: NaN
    with solara.Sidebar():
        solara.Text("sidebar text")
    solara.Button("first button")


@solara.component
def ExplicitAppLayout():
    with solara.AppLayout(title="layout title"):
        with solara.Sidebar():
            solara.Text("sidebar text")
        solara.Text("main content text")


@solara.component
def DatePickerApp():
    import reacton.ipyvuetify as rv

    rv.DatePicker(v_model="2024-01-02")


@solara.component
def LateDatePickerApp():
    # the first render has no Vuetify widget: jupyter-vuetify loads after the root view mounted
    import ipyvue
    import reacton.ipyvue
    import reacton.ipyvuetify as rv

    show, set_show = solara.use_state(False)
    button = ipyvue.Html.element(tag="button", children=["show date picker"])
    reacton.ipyvue.use_event(button, "click", lambda *_ignore: set_show(True))
    if show:
        rv.DatePicker(v_model="2024-01-02")


@solara.component
def DefaultButton():
    solara.Button("default button", color="primary", classes=["default-button"])


@solara.component
def ThemedButton():
    import solara.lab

    solara.lab.theme.themes.light.primary = "#ff0000"
    solara.Button("themed button", color="primary", classes=["themed-button"])


@solara.component
def SingleDollars():
    # a shell prompt in a code block, and prices: no math, so no KaTeX
    solara.Markdown("```bash\n$ pip install solara\n```\n\nPrice ($), single dollar")
    ipywidgets.FloatSlider.element(description="Price ($)")


class Recorder:
    """Collects the requests and console messages of page_session."""

    def __init__(self, page: playwright.sync_api.Page):
        self.page = page
        self.urls: List[str] = []
        self.console: List[playwright.sync_api.ConsoleMessage] = []
        self.failed: List[str] = []
        page.on("request", self._on_request)
        page.on("response", self._on_response)
        page.on("console", self._on_console)

    def _on_request(self, request: playwright.sync_api.Request):
        self.urls.append(request.url)

    def _on_response(self, response: playwright.sync_api.Response):
        if response.status >= 400:
            self.failed.append(f"{response.status} {response.url}")

    def _on_console(self, msg: playwright.sync_api.ConsoleMessage):
        self.console.append(msg)

    def close(self):
        self.page.remove_listener("request", self._on_request)
        self.page.remove_listener("response", self._on_response)
        self.page.remove_listener("console", self._on_console)

    def chunk_requests(self) -> Dict[str, int]:
        return dict(Counter(m.group(1) for m in (CHUNK_RE.search(url) for url in self.urls) if m))

    def lazy_warnings(self) -> List[str]:
        return [m.group(1) for m in (LAZY_RE.search(msg.text) for msg in self.console if msg.type == "warning") if m]

    def errors(self) -> List[str]:
        # a page that is left closes its kernel websocket, which flask reports as a broken frame
        return [msg.text for msg in self.console if msg.type == "error" and not WEBSOCKET_CLOSED_RE.match(msg.text)] + self.failed


@pytest.fixture
def recorder(page_session: playwright.sync_api.Page):
    rec = Recorder(page_session)
    try:
        yield rec
    finally:
        rec.close()


@pytest.fixture(autouse=True)
def default_page_template():
    # server.get_jinja_env is cached per process, with the template directory of the app that was served first.
    # After a test that served the solara website (e.g. api_test), every page would use the website's template,
    # with its third-party scripts that throw on our pages. These tests check the default template.
    solara.server.server.cache_memory.clear()
    yield


@pytest.fixture
def frontend_setting(monkeypatch):
    def set_frontend(value: str):
        monkeypatch.setattr(solara.server.settings.main, "frontend", value)
        # warnings are once per process, every test starts fresh
        monkeypatch.setattr(frontend, "_warned", set())

    return set_frontend


def _server_warnings(caplog) -> List[str]:
    messages = [record.getMessage() for record in caplog.records if record.name == "solara.server.frontend" and record.levelno >= logging.WARNING]
    # Vue 2 logs once that minimal keeps vuetify and mdi; that is not a lazy load
    return [message for message in messages if "build cannot leave out" not in message]


def _expected_chunks() -> List[str]:
    production = solara.server.settings.main.mode == "production"
    return frontend_assets.page_assets(vue3, ipywidgets_major, production, "", frontend.current()).chunk_names


def test_full_preloads_sync(page_session: playwright.sync_api.Page, solara_server, solara_app, extra_include_path, recorder, frontend_setting, caplog):
    frontend_setting("full")

    # record whether the vuetify plugin exists when the page starts the app (solaraInit)
    def add_init_probe(route: playwright.sync_api.Route):
        response = route.fetch()
        html = response.text()
        start = "solaraInit('solara-main')"
        assert start in html
        html = html.replace(start, f"(window.solaraTestVuetifyPluginAtInit = typeof window.vuetifyPlugin, {start})")
        route.fulfill(response=response, body=html)

    def is_page(url: str) -> bool:
        return url.rstrip("/") == solara_server.base_url.rstrip("/")

    page_session.route(is_page, add_init_probe)
    try:
        with caplog.at_level(logging.WARNING, logger="solara.server.frontend"), extra_include_path(HERE), solara_app("frontend_chunks_test:Hello"):
            page_session.goto(solara_server.base_url)
            page_session.locator("text=hello frontend").wait_for()
            if vue3:
                assert page_session.evaluate("window.solaraTestVuetifyPluginAtInit") == "object"
            assert page_session.evaluate("window.solara.loadPreloadedFeaturesSync()") == []
    finally:
        page_session.unroute(is_page, add_init_probe)
    expected = _expected_chunks()
    assert set(expected) >= {"katex", "jupyter-controls", "output-widget", "sanitizer"}
    if vue3:
        assert "vuetify" in expected
    # every preloaded chunk is requested once, and nothing loads lazily (no css-only stubs)
    assert recorder.chunk_requests() == {name: 1 for name in expected}
    assert recorder.lazy_warnings() == []
    assert recorder.errors() == []
    assert _server_warnings(caplog) == []


def test_full_display_outputs(page_session: playwright.sync_api.Page, solara_server, solara_app, extra_include_path, recorder, frontend_setting):
    frontend_setting("full")
    with extra_include_path(HERE), solara_app("frontend_chunks_test:DisplayOutputs"):
        page_session.goto(solara_server.base_url)
        # the first markdown output renders too (it initializes the markdown renderer)
        page_session.locator("strong >> text=md-bold-one").wait_for()
        page_session.locator("strong >> text=md-bold-two").wait_for()
        # code blocks are highlighted by CodeMirror, as before the frontend features
        page_session.locator("code.cm-s-jupyter >> span.cm-variable >> text=x").wait_for()
        if ipywidgets_major >= 8:
            page_session.locator("b >> text=green desc").wait_for()
            assert page_session.locator("b >> text=green desc").get_attribute("style") == "color:rgb(0, 128, 0)"
    assert recorder.lazy_warnings() == []
    assert recorder.errors() == []


def test_minimal_lazy_controls(page_session: playwright.sync_api.Page, solara_server, solara_app, extra_include_path, recorder, frontend_setting, caplog):
    frontend_setting("minimal")
    with caplog.at_level(logging.WARNING, logger="solara.server.frontend"), extra_include_path(HERE), solara_app("frontend_chunks_test:Slider"):
        page_session.goto(solara_server.base_url)
        page_session.locator(".widget-slider >> text=chunk slider").wait_for()
        # the slider is the jupyter-controls slider, so its CSS (jupyter-css) arrived
        page_session.locator(".widget-hslider .slider-container").wait_for()
        # the lazy loaded CSS sits at its slot: in the head, before style.css (the order of a preloaded link)
        css_position = page_session.evaluate(
            """() => {
                const slot = document.querySelector('template[data-solara-css-slot="jupyter-css"]');
                const links = [...document.querySelectorAll('link[rel=stylesheet]')].filter(l => /main\\d\\.jupyter-css\\.css/.test(l.href));
                const style = [...document.querySelectorAll('link[rel=stylesheet]')].find(l => l.href.includes('/static/assets/style.css'));
                return {
                    count: links.length,
                    atSlot: links.length == 1 && slot.previousElementSibling === links[0],
                    beforeStyle: links.length == 1 && !!style && !!(links[0].compareDocumentPosition(style) & Node.DOCUMENT_POSITION_FOLLOWING),
                };
            }"""
        )
    assert css_position == {"count": 1, "atSlot": True, "beforeStyle": True}
    chunks = recorder.chunk_requests()
    assert chunks.get("jupyter-controls") == 1
    assert "katex" not in chunks
    assert "output-widget" not in chunks
    if vue3:
        assert "vuetify" not in chunks
    assert recorder.lazy_warnings() == ["jupyter-controls"]
    assert recorder.errors() == []
    server_warnings = _server_warnings(caplog)
    assert len(server_warnings) == 1
    assert 'Add "+jupyter-controls" to --frontend' in server_warnings[0]


@pytest.mark.parametrize("preset", ["full", "minimal"])
def test_markdown_katex_bundled(page_session: playwright.sync_api.Page, solara_server, solara_app, extra_include_path, recorder, frontend_setting, preset):
    if not vue3 and preset == "minimal":
        pytest.skip("Vue 2 cannot leave out Vuetify, so minimal is not minimal there")
    frontend_setting(preset)
    with extra_include_path(HERE):
        with solara_app("frontend_chunks_test:MarkdownPlain"):
            page_session.goto(solara_server.base_url)
            page_session.locator("text=plain markdown text").wait_for()
            # give a (wrong) katex load the time to start
            page_session.wait_for_timeout(500)
        if preset == "minimal":
            # markdown without math does not load katex
            assert "katex" not in recorder.chunk_requests()
        with solara_app("frontend_chunks_test:MarkdownMath"):
            page_session.goto(solara_server.base_url)
            page_session.locator(".katex >> .mord >> text=E").first.wait_for()
    # the KaTeX of the bundle, not a second copy from the CDN
    assert not [url for url in recorder.urls if "katex@" in url]
    if preset == "minimal":
        assert recorder.chunk_requests().get("katex") == 1
        assert recorder.lazy_warnings() == ["katex"]
    else:
        assert recorder.lazy_warnings() == []
    assert recorder.errors() == []


@pytest.mark.skipif(not vue3, reason="the Vue 2 build has Vuetify in its core bundle")
def test_minimal_hello(page_session: playwright.sync_api.Page, solara_server, solara_app, extra_include_path, recorder, frontend_setting, caplog):
    frontend_setting("minimal")
    with caplog.at_level(logging.WARNING, logger="solara.server.frontend"), extra_include_path(HERE), solara_app("frontend_chunks_test:Hello"):
        page_session.goto(solara_server.base_url)
        page_session.locator("text=hello frontend").wait_for()
        # the pure Vue shell, without Vuetify
        assert page_session.locator(".v-application").count() == 0
        assert page_session.evaluate("typeof window.vuetifyPlugin") == "undefined"
    assert not [url for url in recorder.urls if "jupyter-vuetify" in url]
    assert recorder.chunk_requests() == {}
    assert recorder.lazy_warnings() == []
    assert recorder.errors() == []
    assert _server_warnings(caplog) == []


def test_full_applayout_content_below_app_bar(
    page_session: playwright.sync_api.Page, solara_server, solara_app, extra_include_path, recorder, frontend_setting
):
    # the minified Vuetify CSS must keep the cascade of .v-main: padding-top stays 64px, so the content is not under the app bar
    frontend_setting("full")
    with extra_include_path(HERE), solara_app("frontend_chunks_test:SidebarApp"):
        page_session.goto(solara_server.base_url)
        button = page_session.locator("button >> text=first button")
        button.wait_for()
        page_session.locator("text=sidebar text").wait_for()
        app_bar = page_session.locator(".v-app-bar, .v-toolbar").first
        app_bar.wait_for()
        app_bar_box = app_bar.bounding_box()
        button_box = button.bounding_box()
        assert app_bar_box is not None and button_box is not None
        assert button_box["y"] >= app_bar_box["y"] + app_bar_box["height"]
    assert recorder.errors() == []


def test_full_markdown_katex_globals(page_session: playwright.sync_api.Page, solara_server, solara_app, extra_include_path, recorder, frontend_setting):
    # as before the frontend features: the first Markdown makes KaTeX available to user code
    frontend_setting("full")
    with extra_include_path(HERE), solara_app("frontend_chunks_test:MarkdownPlain"):
        page_session.goto(solara_server.base_url)
        page_session.locator("text=plain markdown text").wait_for()
        page_session.wait_for_function("typeof window.renderMathInElement === 'function'")
        katex_render = page_session.evaluate("new Promise((resolve, reject) => requirejs(['katex'], katex => resolve(katex.renderToString('x')), reject))")
        assert "katex" in katex_render
    assert not [url for url in recorder.urls if "katex@" in url]
    assert recorder.lazy_warnings() == []
    assert recorder.errors() == []


@pytest.mark.skipif(not vue3, reason="the Vue 2 build has Vuetify in its core bundle")
def test_minimal_explicit_applayout(page_session: playwright.sync_api.Page, solara_server, solara_app, extra_include_path, recorder, frontend_setting):
    # the page without Vuetify has no <v-app>: AppLayout provides the layout its drawer, app bar and main need
    frontend_setting("minimal")
    page_errors: List[str] = []

    def on_page_error(error):
        page_errors.append(str(error))

    page_session.on("pageerror", on_page_error)
    try:
        with extra_include_path(HERE), solara_app("frontend_chunks_test:ExplicitAppLayout"):
            page_session.goto(solara_server.base_url)
            page_session.locator("text=main content text").wait_for()
            page_session.locator("text=sidebar text").wait_for()
            page_session.locator("text=layout title").wait_for()
    finally:
        page_session.remove_listener("pageerror", on_page_error)
    assert page_errors == []
    assert recorder.lazy_warnings() == ["vuetify"]


@pytest.mark.skipif(not vue3, reason="the Vue 2 build has Vuetify in its core bundle")
def test_minimal_date_picker(page_session: playwright.sync_api.Page, solara_server, solara_app, extra_include_path, recorder, frontend_setting):
    # jupyter-vuetify loads after the shell app exists: its components (IpyvuetifyDatePicker) are registered on it too
    frontend_setting("minimal")
    with extra_include_path(HERE), solara_app("frontend_chunks_test:DatePickerApp"):
        page_session.goto(solara_server.base_url)
        page_session.locator(".v-date-picker").wait_for()
    assert not [msg.text for msg in recorder.console if "Failed to resolve component" in msg.text]
    assert recorder.lazy_warnings() == ["vuetify"]


@pytest.mark.skipif(not vue3, reason="the Vue 2 build has Vuetify in its core bundle")
def test_minimal_date_picker_after_mount(page_session: playwright.sync_api.Page, solara_server, solara_app, extra_include_path, recorder, frontend_setting):
    # jupyter-vuetify loads after the root view mounted: its components are still registered on the shell app
    frontend_setting("minimal")
    with extra_include_path(HERE), solara_app("frontend_chunks_test:LateDatePickerApp"):
        page_session.goto(solara_server.base_url)
        page_session.locator("button >> text=show date picker").click()
        page_session.locator(".v-date-picker").wait_for(timeout=10000)
        assert page_session.locator("ipyvuetifydatepicker").count() == 0
    assert not [msg.text for msg in recorder.console if "Failed to resolve component" in msg.text]
    assert recorder.lazy_warnings() == ["vuetify"]


@pytest.mark.parametrize("preset", ["full", "minimal"])
def test_markdown_katex_svg_height(page_session: playwright.sync_api.Page, solara_server, solara_app, extra_include_path, recorder, frontend_setting, preset):
    # KaTeX's `.katex svg {height: inherit}` must win over style.css's `.jp-RenderedHTMLCommon svg {height: auto}`,
    # as before the frontend features, or the radical of \sqrt collapses to a line
    frontend_setting(preset)
    with extra_include_path(HERE), solara_app("frontend_chunks_test:MarkdownSqrt"):
        page_session.goto(solara_server.base_url)
        svg = page_session.locator(".solara-markdown .katex .hide-tail svg").first
        svg.wait_for()
        page_session.wait_for_function("document.querySelector('.solara-markdown .katex .hide-tail svg').getBoundingClientRect().height > 5", timeout=5000)
    assert recorder.errors() == []


# a stand-in for MathJax 2 (that a page can load, e.g. from assets/custom.js): it records what it typesets
FAKE_MATHJAX = """<script>
window.solaraTestMathJaxTypeset = [];
window.MathJax = {Hub: {Queue: (job) => window.solaraTestMathJaxTypeset.push(job[0])}};
</script>"""


def test_full_markdown_mathjax_first(page_session: playwright.sync_api.Page, solara_server, solara_app, extra_include_path, recorder, frontend_setting):
    # as before the frontend features: with MathJax 2 on the page, Markdown typesets with MathJax, not with KaTeX
    frontend_setting("full")

    def add_fake_mathjax(route: playwright.sync_api.Route):
        response = route.fetch()
        html = response.text()
        assert "<head>" in html
        route.fulfill(response=response, body=html.replace("<head>", "<head>" + FAKE_MATHJAX, 1))

    def is_page(url: str) -> bool:
        return url.rstrip("/") == solara_server.base_url.rstrip("/")

    page_session.route(is_page, add_fake_mathjax)
    try:
        with extra_include_path(HERE), solara_app("frontend_chunks_test:MarkdownMath"):
            page_session.goto(solara_server.base_url)
            page_session.locator("text=math markdown").wait_for()
            page_session.wait_for_function("window.solaraTestMathJaxTypeset.length > 0")
            assert page_session.evaluate("window.solaraTestMathJaxTypeset[0]") == "Typeset"
            assert page_session.locator(".solara-markdown .katex").count() == 0
            assert page_session.locator("link[data-solara-katex-css-last]").count() == 0
    finally:
        page_session.unroute(is_page, add_fake_mathjax)
    assert recorder.errors() == []


def test_minimal_fragment_container(
    page_session: playwright.sync_api.Page, solara_server, solara_app, extra_include_path, recorder, frontend_setting, monkeypatch
):
    # SOLARA_DEFAULT_CONTAINER=Fragment: the fragment widgets (VBoxes) do not make the page load jupyter-controls
    monkeypatch.setattr(reacton.core, "_default_container", solara.components.misc._DefaultFragment)
    frontend_setting("minimal")
    with extra_include_path(HERE), solara_app("frontend_chunks_test:TwoTexts"):
        page_session.goto(solara_server.base_url)
        page_session.locator("text=first fragment text").wait_for()
        page_session.locator("text=second fragment text").wait_for()
    chunks = recorder.chunk_requests()
    assert "jupyter-controls" not in chunks
    assert "jupyter-controls" not in recorder.lazy_warnings()
    assert recorder.errors() == []


@pytest.mark.skipif(not vue3, reason="the Vue 2 build has Vuetify in its core bundle")
@pytest.mark.parametrize("preset", ["full", "minimal"])
def test_vuetify_theme_colors(page_session: playwright.sync_api.Page, solara_server, solara_app, extra_include_path, recorder, frontend_setting, preset):
    # Vuetify that loads on first use (minimal) gets the theme of solara.lab.theme, as in full
    frontend_setting(preset)
    with extra_include_path(HERE):
        with solara_app("frontend_chunks_test:DefaultButton"):
            page_session.goto(solara_server.base_url)
            # the default primary color of solara.lab.theme (ipyvuetify's #6200EE), not Vuetify's own default
            playwright.sync_api.expect(page_session.locator(".default-button")).to_have_css("background-color", "rgb(98, 0, 238)")
        with solara_app("frontend_chunks_test:ThemedButton"):
            page_session.goto(solara_server.base_url)
            playwright.sync_api.expect(page_session.locator(".themed-button")).to_have_css("background-color", "rgb(255, 0, 0)")
    # two pages: each loads Vuetify on first use
    assert recorder.lazy_warnings() == ([] if preset == "full" else ["vuetify", "vuetify"])
    assert recorder.errors() == []


def test_minimal_single_dollar_no_katex(
    page_session: playwright.sync_api.Page, solara_server, solara_app, extra_include_path, recorder, frontend_setting, caplog
):
    frontend_setting("minimal,+jupyter-controls")
    with caplog.at_level(logging.WARNING, logger="solara.server.frontend"), extra_include_path(HERE), solara_app("frontend_chunks_test:SingleDollars"):
        page_session.goto(solara_server.base_url)
        page_session.locator("text=single dollar").wait_for()
        page_session.locator(".widget-slider >> text=Price ($)").wait_for()
        # give a (wrong) katex load the time to start
        page_session.wait_for_timeout(500)
    assert "katex" not in recorder.chunk_requests()
    assert "katex" not in recorder.lazy_warnings()
    assert not [message for message in _server_warnings(caplog) if "katex" in message]
    assert recorder.errors() == []
