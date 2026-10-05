"""The Python side of the --frontend setting: widgets without jupyter-controls, and the warning for a feature that is not preloaded."""

import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import ipyvue
import ipyvuetify as v
import ipywidgets
import pytest

import solara
import solara.server.app
import solara.server.settings
from solara.server import frontend
from solara.server.app import AppScript

FRONTEND_LOGGER = "solara.server.frontend"


@pytest.fixture
def warned(monkeypatch):
    # the warnings are once per feature per process, start each test fresh
    monkeypatch.setattr(frontend, "_warned", set())


@pytest.fixture
def minimal(monkeypatch, warned):
    """A server with --frontend=minimal (Vue 3, also on the Vue 2 test lane)."""
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
            # the page preloaded only vuetify (it was rendered when the setting was minimal)
            page_frontend = {"spec": "minimal", "features": ["vuetify", "mdi", "roboto", "vuetify-css"], "chunks": ["vuetify"]}
            comm.receive({"method": "run", "args": {"path": "/", "appName": None, "frontend": page_frontend}})
            assert "jupyter-controls" not in frontend.active()
            comm.receive({"method": "reload", "path": "/"})
            assert frontend.active().spec == "minimal"
        # without the frontend of the page (an older page), the server setting applies
        kernel_context.frontend = None
        with kernel_context:
            assert "jupyter-controls" in frontend.active()
    finally:
        app.close()


def test_warning_once_per_feature(minimal, caplog):
    ipywidgets.Button(description="one")
    ipywidgets.Button(description="two")
    messages = frontend_warnings(caplog)
    assert len(messages) == 1
    assert "'jupyter-controls'" in messages[0]
    assert "--frontend=minimal,+jupyter-controls" in messages[0]


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


def test_lazy_load_message_names_the_module(minimal, kernel_context, caplog):
    # the server cannot know which widgets ask requirejs for a module of lumino (e.g. a widget of an nbextension), so
    # the browser's report is the only warning; it names the module that asked
    comm = FakeComm()
    solara.server.app.solara_comm_target(comm, None)
    comm.receive({"method": "frontend-lazy-load", "feature": "lumino", "module": "@phosphor/widgets"})
    comm.receive({"method": "frontend-lazy-load", "feature": "lumino", "module": "@lumino/widgets"})
    messages = frontend_warnings(caplog)
    assert len(messages) == 1
    assert "The requirejs module '@phosphor/widgets' of the page needs the frontend feature 'lumino'" in messages[0]
    assert "--frontend=minimal,+lumino" in messages[0]


def test_lazy_load_message_ignores_a_strange_module(minimal, kernel_context, caplog):
    comm = FakeComm()
    solara.server.app.solara_comm_target(comm, None)
    # the browser sends it, and it shows up in the log: a value that is not a module name is left out
    comm.receive({"method": "frontend-lazy-load", "feature": "lumino", "module": "@lumino/widgets\n"})
    messages = frontend_warnings(caplog)
    assert len(messages) == 1
    assert messages[0].startswith("The page needs the frontend feature 'lumino'")


def test_errors_without_controls(minimal, kernel_context, no_kernel_context):
    with kernel_context:
        widget = solara.server.app._error_widget("<b>Traceback</b>")
        assert type(widget) is ipyvue.Html
        assert widget.tag == "pre"
        # Vue renders the children as text, no escaping needed
        assert widget.children == ["<b>Traceback</b>"]
    element = solara.server.app._error_element("Traceback")
    assert element.component.widget is ipyvue.Html
