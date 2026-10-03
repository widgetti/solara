"""The Python side of the --frontend setting: widgets without Vuetify, and the warning for a feature that is not preloaded."""

import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import ipyvue
import ipyvuetify as v
import ipywidgets
import pytest
import reacton.core

import solara
import solara.components.misc
import solara.server.app
import solara.server.settings
import solara.widgets
import solara.widgets.widgets
from solara.components.code_highlight_css import CodeHighlightCss, CodeHighlightCssWidget, CodeHighlightCssWidgetVue
from solara.components.echarts import EchartsWidget, EchartsWidgetVue
from solara.components.head_tag import HeadTag, HeadTagWidget, HeadTagWidgetVue
from solara.components.markdown_editor import MarkdownEditorWidget, MarkdownEditorWidgetVue
from solara.components.pivot_table import PivotTableWidget, PivotTableWidgetVue
from solara.components.title import TitleWidget, TitleWidgetVue
from solara.server import frontend
from solara.server.app import AppScript

FRONTEND_LOGGER = "solara.server.frontend"


@pytest.fixture
def warned(monkeypatch):
    # the warnings are once per feature per process, start each test fresh
    monkeypatch.setattr(frontend, "_warned", set())


@pytest.fixture
def minimal(monkeypatch, warned):
    """A server with --frontend=minimal. Vue 3, also on the Vue 2 test lane, because Vue 2 keeps Vuetify."""
    monkeypatch.setattr(solara.server.settings.main, "frontend", "minimal")
    monkeypatch.setattr(frontend, "vue3", True)


def render(element):
    # the default container is an ipywidgets VBox, which needs the jupyter-controls feature
    return solara.render(element, container=ipyvue.Html(tag="div"), handle_error=False)


def frontend_warnings(caplog) -> List[str]:
    return [record.getMessage() for record in caplog.records if record.name == FRONTEND_LOGGER and record.levelno >= logging.WARNING]


class FakeComm:
    def __init__(self):
        self.sent: List[Dict[str, Any]] = []
        self.on_msg_callback: Optional[Callable] = None

    def on_msg(self, callback):
        self.on_msg_callback = callback

    def send(self, data):
        self.sent.append(data)

    def receive(self, data):
        assert self.on_msg_callback is not None
        self.on_msg_callback({"content": {"data": data}})


def test_minimal_hello_has_no_vuetify_models(minimal, kernel_context, no_kernel_context, tmp_path: Path, monkeypatch, caplog):
    app_file = tmp_path / "hello.py"
    app_file.write_text("import solara\n\n\n@solara.component\ndef Page():\n    solara.Text('hello')\n")
    app = AppScript(str(app_file))
    monkeypatch.setitem(solara.server.app.apps, "__default__", app)
    try:
        app.init()
        with kernel_context:
            comm = FakeComm()
            solara.server.app.solara_comm_target(comm, None)
            # the page without Vuetify sends no themes
            comm.receive({"method": "run", "args": {"path": "/", "appName": None}})
            assert comm.sent[-1]["method"] == "finished"
            assert type(kernel_context.container) is ipyvue.Html
            modules = {widget._model_module for widget in kernel_context.widgets.values()}
            assert "jupyter-vue" in modules
            assert "jupyter-vuetify" not in modules
            assert "@jupyter-widgets/controls" not in modules
            texts = [widget for widget in kernel_context.widgets.values() if isinstance(widget, ipyvue.Html) and widget.children == ["hello"]]
            assert len(texts) == 1
    finally:
        app.close()
    assert frontend_warnings(caplog) == []


def _jupyter_vuetify_widgets(context) -> List[ipywidgets.Widget]:
    return [widget for widget in context.widgets.values() if widget._model_module == "jupyter-vuetify"]


def test_theme_when_vuetify_loads_on_first_use(minimal, kernel_context, no_kernel_context, tmp_path: Path, monkeypatch):
    from solara.lab.components.theming import theme

    app_file = tmp_path / "hello.py"
    app_file.write_text("import solara\n\n\n@solara.component\ndef Page():\n    solara.Text('hello')\n")
    app = AppScript(str(app_file))
    monkeypatch.setitem(solara.server.app.apps, "__default__", app)
    try:
        app.init()
        with kernel_context:
            comm = FakeComm()
            solara.server.app.solara_comm_target(comm, None)
            themes = {"light": {"primary": "#123456"}, "dark": {}}
            comm.receive({"method": "run", "args": {"path": "/", "appName": None, "themes": themes, "dark": False}})
            # the theme widgets are Vuetify widgets: the page does not need them before it loads Vuetify
            assert _jupyter_vuetify_widgets(kernel_context) == []
            comm.receive({"method": "frontend-lazy-load", "feature": "vuetify"})
            # the theme of the page, as in full, so Vuetify widgets get the same colors
            assert {type(widget).__name__ for widget in _jupyter_vuetify_widgets(kernel_context)} == {"Theme", "ThemeColors"}
            assert theme.themes.light.primary == "#123456"
            assert theme.dark_effective is False
            count = len(kernel_context.widgets)
            comm.receive({"method": "frontend-lazy-load", "feature": "vuetify"})
            assert len(kernel_context.widgets) == count
            # a hot reload keeps the theme, as in full
            theme.themes.light.secondary = "#654321"
            comm.receive({"method": "reload", "path": "/"})
            assert comm.sent[-1]["method"] == "finished"
            assert theme.themes.light.primary == "#123456"
            assert theme.themes.light.secondary == "#654321"
    finally:
        app.close()


@pytest.mark.parametrize("preset", ["full", "minimal"])
def test_theme_changes_of_the_app_win(preset, warned, kernel_context, no_kernel_context, tmp_path: Path, monkeypatch):
    # the theming docs: Page sets a color, and the page sends the colors of its theme.js with run
    from solara.lab.components.theming import theme

    monkeypatch.setattr(solara.server.settings.main, "frontend", preset)
    monkeypatch.setattr(frontend, "vue3", True)
    app_file = tmp_path / "themed.py"
    app_file.write_text(
        "import solara\nimport solara.lab\n\n\n@solara.component\ndef Page():\n"
        "    solara.lab.theme.themes.light.primary = '#3f51b5'\n    solara.Text('hello')\n"
    )
    app = AppScript(str(app_file))
    monkeypatch.setitem(solara.server.app.apps, "__default__", app)
    try:
        app.init()
        with kernel_context:
            comm = FakeComm()
            solara.server.app.solara_comm_target(comm, None)
            themes = {"light": {"colors": {"primary": "#ff991f", "secondary": "#123456"}}, "dark": {}}
            comm.receive({"method": "run", "args": {"path": "/", "appName": None, "themes": themes, "dark": True}})
            assert comm.sent[-1]["method"] == "finished"
            assert theme.themes.light.primary == "#3f51b5"
            assert theme.themes.light.secondary == "#123456"
            assert theme.dark_effective is True
            # the page loads Vuetify on first use (minimal): the theme keeps the change of the app
            comm.receive({"method": "frontend-lazy-load", "feature": "vuetify"})
            assert theme.themes.light.primary == "#3f51b5"
            assert theme.themes.light.secondary == "#123456"
            assert theme.dark_effective is True
            comm.receive({"method": "reload", "path": "/"})
            assert comm.sent[-1]["method"] == "finished"
            assert theme.themes.light.primary == "#3f51b5"
            assert theme.themes.light.secondary == "#123456"
    finally:
        app.close()


def test_page_keeps_its_frontend(warned, kernel_context, no_kernel_context, tmp_path: Path, monkeypatch):
    # e.g. solara.server.settings.main.frontend in the app code, which a hot reload changes
    monkeypatch.setattr(frontend, "vue3", True)
    monkeypatch.setattr(solara.server.settings.main, "frontend", "full")
    app_file = tmp_path / "hello.py"
    app_file.write_text("import solara\n\n\n@solara.component\ndef Page():\n    solara.Text('hello')\n")
    app = AppScript(str(app_file))
    monkeypatch.setitem(solara.server.app.apps, "__default__", app)
    try:
        app.init()
        with kernel_context:
            comm = FakeComm()
            solara.server.app.solara_comm_target(comm, None)
            # the page preloaded nothing (it was rendered when the setting was minimal)
            page_frontend = {"spec": "minimal", "features": [], "chunks": []}
            comm.receive({"method": "run", "args": {"path": "/", "appName": None, "frontend": page_frontend}})
            assert type(kernel_context.container) is ipyvue.Html
            assert not frontend.vuetify_enabled()
            assert frontend.active().spec == "minimal"
            before = set(kernel_context.widgets)
            comm.receive({"method": "reload", "path": "/"})
            new_widgets = [widget for key, widget in kernel_context.widgets.items() if key not in before]
            assert new_widgets
            # still widgets for the page without Vuetify, not the AppLayout of full
            assert [widget for widget in new_widgets if widget._model_module == "jupyter-vuetify"] == []
        # without the frontend of the page (an older page), the server setting applies
        kernel_context.frontend = None
        with kernel_context:
            assert frontend.vuetify_enabled()
    finally:
        app.close()


def test_warning_once_per_feature(minimal, caplog):
    v.Btn(children=["one"])
    v.Btn(children=["two"])
    messages = frontend_warnings(caplog)
    assert len(messages) == 1
    assert "ipyvuetify" in messages[0]
    assert "'vuetify'" in messages[0]
    assert "--frontend=minimal,+vuetify" in messages[0]


def test_no_warning_in_full(warned, caplog):
    v.Btn(children=["one"])
    ipywidgets.Button(description="two")
    assert frontend_warnings(caplog) == []


def test_no_warning_without_kernel_context(minimal, no_kernel_context, monkeypatch, caplog):
    checked: List[Any] = []
    monkeypatch.setattr(frontend, "check_widget", checked.append)
    v.Btn(children=["one"])
    assert checked == []
    assert frontend_warnings(caplog) == []


def test_lazy_load_message_logs_once(minimal, kernel_context, caplog):
    comm = FakeComm()
    solara.server.app.solara_comm_target(comm, None)
    comm.receive({"method": "frontend-lazy-load", "feature": "katex"})
    comm.receive({"method": "frontend-lazy-load", "feature": "katex"})
    comm.receive({"method": "frontend-lazy-load", "feature": "no-such-feature"})
    messages = frontend_warnings(caplog)
    assert len(messages) == 1
    assert "--frontend=minimal,+katex" in messages[0]


def test_row_column_without_vuetify(minimal):
    @solara.component
    def Test():
        with solara.Column(gap="5px", margin=2, classes=["mine"], style={"color": "red"}) as main:
            with solara.Row(justify="center"):
                solara.Text("hi")
            solara.Div(children=["div"])
        return main

    _box, rc = render(Test())
    try:
        column = rc.find(ipyvue.Html, class_="solara-column mine").widget
        assert type(column) is ipyvue.Html
        assert column._model_module == "jupyter-vue"
        assert column.style_ == "display: flex; flex-direction: column; align-items: stretch; row-gap: 5px; margin: 8px;color:red;;"
        row = rc.find(ipyvue.Html, class_="solara-row").widget
        assert type(row) is ipyvue.Html
        assert "justify-content: center;" in row.style_
        text = rc.find(ipyvue.Html, children=["hi"]).widget
        assert type(text) is ipyvue.Html
        assert text.tag == "span"
        div = rc.find(ipyvue.Html, children=["div"]).widget
        assert type(div) is ipyvue.Html
        assert div.tag == "div"
        rc.find(v.Sheet).assert_empty()
    finally:
        rc.close()


def test_column_full_is_unchanged():
    @solara.component
    def Test():
        with solara.Column(gap="5px", margin=2, classes=["mine"], style={"color": "red"}) as main:
            solara.Text("x")
        return main

    _box, rc = render(Test())
    try:
        sheet = rc.find(v.Sheet).widget
        assert sheet.class_ == "d-flex ma-2 mine"
        assert sheet.style_ == "flex-direction: column; align-items: stretch; row-gap: 5px;color:red;;"
        assert type(rc.find(ipyvue.Html, children=["x"]).widget) is v.Html
    finally:
        rc.close()


# (Vuetify class, as before; the class without Vuetify) for solara's templates without Vuetify tags
TEMPLATE_CLASSES = [
    (solara.widgets.VegaLite, solara.widgets.widgets.VegaLiteVue),
    (solara.widgets.Navigator, solara.widgets.widgets.NavigatorVue),
    (solara.widgets.GridLayout, solara.widgets.widgets.GridLayoutVue),
    (solara.widgets.HTML, solara.widgets.widgets.HTMLVue),
    (TitleWidget, TitleWidgetVue),
    (HeadTagWidget, HeadTagWidgetVue),
    (EchartsWidget, EchartsWidgetVue),
    (PivotTableWidget, PivotTableWidgetVue),
    (CodeHighlightCssWidget, CodeHighlightCssWidgetVue),
    (MarkdownEditorWidget, MarkdownEditorWidgetVue),
]


@pytest.mark.parametrize("vuetify_class,vue_class", TEMPLATE_CLASSES)
def test_template_classes(vuetify_class, vue_class):
    # the public class is the same VuetifyTemplate as before, for Jupyter and full mode
    widget = vuetify_class()
    assert isinstance(widget, v.VuetifyTemplate)
    assert widget._model_module == "jupyter-vuetify"
    assert widget._view_module == "jupyter-vuetify"
    widget_vue = vue_class()
    assert not isinstance(widget_vue, v.VuetifyTemplate)
    assert widget_vue._model_module == "jupyter-vue"
    assert widget_vue._view_module == "jupyter-vue"
    assert set(widget.keys) == set(widget_vue.keys)
    template = widget_vue.template if isinstance(widget_vue.template, str) else widget_vue.template.template
    # if a template starts to use Vuetify, it should only be a VuetifyTemplate again
    assert "<v-" not in template
    assert "$vuetify" not in template


@solara.component
def TemplateComponents():
    with solara.Div() as main:
        solara.Title("title")
        HeadTag(tagname="meta", key="description", attributes={"name": "description", "content": "x"})
        solara.HTML(tag="b", unsafe_innerHTML="html")
        solara.Navigator(location="/")
        solara.GridDraggable(items=[], grid_layout=[])
        solara.FigureEcharts(option={})
        solara.PivotTableView(data={"no": "data"})
        CodeHighlightCss()
        solara.MarkdownEditor("markdown")
        solara.Style(".x { color: red; }")
    return main


def test_template_components_full():
    _box, rc = render(TemplateComponents())
    try:
        for vuetify_class, _vue_class in TEMPLATE_CLASSES:
            if vuetify_class is solara.widgets.VegaLite:
                continue  # needs altair, see figure_altair_test.py
            assert type(rc.find(vuetify_class).widget) is vuetify_class
        (style,) = (widget for widget in rc.find(ipyvue.VueTemplate).widgets if ".x { color: red; }" in str(widget.template))
        assert type(style) is v.VuetifyTemplate
    finally:
        rc.close()


def test_template_components_without_vuetify(minimal, caplog):
    _box, rc = render(TemplateComponents())
    try:
        rc.find(v.VuetifyTemplate).assert_empty()
        for vuetify_class, vue_class in TEMPLATE_CLASSES:
            if vuetify_class is solara.widgets.VegaLite:
                continue
            assert type(rc.find(vue_class).widget) is vue_class
        (style,) = (widget for widget in rc.find(ipyvue.VueTemplate).widgets if ".x { color: red; }" in str(widget.template))
        assert type(style) is ipyvue.VueTemplate
    finally:
        rc.close()
    assert frontend_warnings(caplog) == []


def test_errors_without_vuetify_and_controls(minimal, kernel_context, no_kernel_context, tmp_path: Path):
    with kernel_context:
        widget = solara.server.app._error_widget("<b>Traceback</b>")
        assert type(widget) is ipyvue.Html
        assert widget.tag == "pre"
        # Vue renders the children as text, no escaping needed
        assert widget.children == ["<b>Traceback</b>"]
    element = solara.server.app._error_element("Traceback")
    assert element.component.widget is ipyvue.Html

    # an app without Page: autorouting shows the error in a Column instead of an AppLayout
    app_file = tmp_path / "nopage.py"
    app_file.write_text("import solara\n\nx = 1\n")
    app = AppScript(str(app_file))
    try:
        app.init()
        with kernel_context:
            main = app.run()
            root = solara.RoutingProvider(children=[main], routes=app.routes, pathname="/")
            _box, rc = render(root)
            try:
                rc.find(ipyvue.Html, class_="solara-column").assert_not_empty()
                assert "No object with name Page found" in rc.find(v.Alert).widget.children[0]
                rc.find(v.AppBar).assert_empty()
            finally:
                rc.close()
    finally:
        app.close()


@solara.component
def PortalsWithoutLayout():
    with solara.Sidebar():
        solara.Text("sidebar filters")
    with solara.AppBarTitle():
        solara.Text("My App Title")
    solara.Text("main content")


def test_portal_without_layout_warns(minimal, kernel_context, caplog):
    # without vuetify there is no default layout (AppLayout), so nothing shows the Sidebar and AppBarTitle children
    _box, rc = render(PortalsWithoutLayout())
    rc.render(PortalsWithoutLayout())
    rc.close()
    messages = frontend_warnings(caplog)
    assert len(messages) == 2
    assert messages[0].startswith("solara.Sidebar: ")
    assert messages[1].startswith("solara.AppBarTitle: ")
    assert '"+vuetify"' in messages[0]


def test_portal_without_layout_full_no_warning(warned, kernel_context, caplog):
    _box, rc = render(PortalsWithoutLayout())
    rc.close()
    assert frontend_warnings(caplog) == []


@solara.component
def TwoTexts():
    solara.Text("first text")
    solara.Text("second text")


@pytest.fixture
def fragment_container(monkeypatch):
    # SOLARA_DEFAULT_CONTAINER=Fragment, as in the 'solara 2.0' CI run
    monkeypatch.setattr(reacton.core, "_default_container", solara.components.misc._DefaultFragment)


def fragment_widgets(kernel_context) -> List[ipywidgets.Widget]:
    return [widget for widget in kernel_context.widgets.values() if isinstance(widget, reacton.core.FragmentWidget)]


def test_fragment_container_without_controls(minimal, fragment_container, kernel_context, caplog):
    # the fragment widget (a VBox) needs no jupyter-controls in the browser
    _box, rc = render(TwoTexts())
    try:
        fragments = fragment_widgets(kernel_context)
        assert fragments
        assert all(type(widget) is solara.widgets.widgets.FragmentVue for widget in fragments)
        assert fragments[0].get_state()["_model_module"] == "jupyter-vue"
    finally:
        rc.close()
    assert frontend_warnings(caplog) == []


def test_fragment_container_full_is_unchanged(warned, fragment_container, kernel_context, caplog):
    _box, rc = render(TwoTexts())
    try:
        fragments = fragment_widgets(kernel_context)
        assert fragments
        assert all(type(widget) is reacton.core.FragmentWidget for widget in fragments)
    finally:
        rc.close()
    assert frontend_warnings(caplog) == []


@solara.component
def SidebarAppLayout():
    with solara.AppLayout(title="layout title"):
        with solara.Sidebar():
            solara.Text("sidebar")
        solara.Text("main content")


def test_applayout_without_vuetify_provides_the_layout(minimal, kernel_context):
    # the page without Vuetify has no <v-app>, but Vuetify's drawer, app bar and main need the layout it provides
    box, rc = render(SidebarAppLayout())
    try:
        assert type(box.children[0]) is v.App
    finally:
        rc.close()


def test_applayout_full_is_unchanged(warned, kernel_context):
    box, rc = render(SidebarAppLayout())
    try:
        assert type(box.children[0]) is v.Html
    finally:
        rc.close()


def test_solara_check_without_vuetify(minimal, kernel_context, caplog, tmp_path: Path, monkeypatch):
    import solara.checks

    monkeypatch.setattr(solara.checks, "solara_checked_path", tmp_path / ".solara_checked")
    _box, rc = render(solara.checks.SolaraCheck())
    try:
        rc.find(v.Html).assert_empty()
        assert rc.find(ipyvue.Html, tag="iframe").widget.style_ == "display: none;"
    finally:
        rc.close()
    assert frontend_warnings(caplog) == []


def test_component_vue_warning_names_vuetify_false(minimal, tmp_path: Path, caplog):
    vue_file = tmp_path / "plain.vue"
    vue_file.write_text("<template><span>plain</span></template>\n")

    @solara.component_vue(str(vue_file))
    def Plain():
        pass

    @solara.component_vue(str(vue_file), vuetify=False)
    def PlainVue():
        pass

    _box, rc = render(PlainVue())
    rc.close()
    assert frontend_warnings(caplog) == []
    _box, rc = render(Plain())
    rc.close()
    messages = frontend_warnings(caplog)
    assert len(messages) == 1
    assert "plain.vue" in messages[0]
    assert "pass vuetify=False" in messages[0]
