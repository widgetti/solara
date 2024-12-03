import logging
import sys
from pathlib import Path

import ipyvuetify as v
import ipywidgets
import reacton.core

# import pytest
import solara

# import solara.server.app
from solara.server import reload
from solara.server.app import AppScript

logger = logging.getLogger("solara.server.app_test")


HERE = Path(__file__).parent
reload.reloader.start()


def test_notebook_element(kernel_context, no_kernel_context):
    name = str(HERE / "solara_test_apps" / "notebookapp_element.ipynb")
    app = AppScript(name)
    try:
        with kernel_context:
            el = app.run()
            assert isinstance(el, reacton.core.Element)
            el2 = app.run()
            assert el is el2
    finally:
        app.close()


def test_notebook_component(kernel_context, no_kernel_context):
    name = str(HERE / "solara_test_apps" / "notebookapp_component.ipynb")
    app = AppScript(name)
    try:
        with kernel_context:
            el = app.run()
            assert isinstance(el, reacton.core.Element)
            el2 = app.run()
            assert el is el2
    finally:
        app.close()


def test_notebook_widget(kernel_context, no_kernel_context):
    name = str(HERE / "solara_test_apps" / "notebookapp_widget.ipynb")
    app = AppScript(name)
    try:
        with kernel_context:
            el = app.run()
            root = solara.RoutingProvider(children=[el], routes=app.routes, pathname="/")
            _box, rc = solara.render(root, handle_error=False)
            widget1 = rc.find(ipywidgets.Button, description="Click me").widget
            assert isinstance(widget1, ipywidgets.Button)
            _box, rc = solara.render(root, handle_error=False)
            widget2 = rc.find(ipywidgets.Button, description="Click me").widget
        assert widget1 is not widget2
    finally:
        app.close()


def test_sidebar_single_file_multiple_routes(kernel_context, no_kernel_context):
    name = str(HERE / "solara_test_apps" / "single_file_multiple_routes.py")
    app = AppScript(name)
    try:
        with kernel_context:
            c = app.run()
            root = solara.RoutingProvider(children=[c], routes=app.routes, pathname="/")
            box, rc = solara.render(root, handle_error=False)
            assert rc.find(v.Slider, label="in sidebar")
    finally:
        app.close()


def test_sidebar_single_file(kernel_context, no_kernel_context):
    name = str(HERE / "solara_test_apps" / "single_file.py")
    app = AppScript(name)
    try:
        with kernel_context:
            c = app.run()
            root = solara.RoutingProvider(children=[c], routes=app.routes, pathname="/")
            box, rc = solara.render(root, handle_error=False)
            assert rc.find(v.Slider, label="in sidebar")
    finally:
        app.close()


def test_sidebar_single_file_missing(kernel_context, no_kernel_context):
    name = str(HERE / "solara_test_apps" / "single_file.py:doesnotexist")
    app = AppScript(name)
    try:
        with kernel_context:
            c = app.run()
            root = solara.RoutingProvider(children=[c], routes=app.routes, pathname="/")
            box, rc = solara.render(root, handle_error=False)
            assert "No object with name doesnotexist" in rc.find(v.Alert).widget.children[0]
    finally:
        app.close()


# these make other test fail on CI (vaex is used, which causes a blake3 reload, which fails)
def test_watch_module_reload(tmpdir, kernel_context, extra_include_path, no_kernel_context):
    import ipyvuetify as v

    with extra_include_path(str(tmpdir)):
        py_file = tmpdir / "test.py"
        py_mod_file = tmpdir / "somemod.py"

        logger.info("writing files")
        with open(py_mod_file, "w") as f:
            f.write("import ipyvuetify as v; page = v.Btn.element(children=['first'])\n")
        with open(py_file, "w") as f:
            f.write("import somemod; page=somemod.page\n")

        logger.info("wrote files")

        app = AppScript(f"{py_file}")
        try:
            result = app.run()
            assert "somemod" in sys.modules
            assert "somemod" in reload.reloader.watched_modules
            somemod1 = sys.modules["somemod"]
            root = solara.RoutingProvider(children=[result], routes=app.routes, pathname="/")
            box, rc = solara.render(root, handle_error=False)
            assert rc.find(v.Btn, children=["first"])
            # assert result.component.widget == v.Btn

            # change depending module
            with open(py_mod_file, "w") as f:
                f.write("import ipyvuetify as v; page = v.Card.element(children=['second'])\n")
            # wait for the event to trigger
            reload.reloader.reload_event_next.wait()
            # assert "somemod" not in sys.modules
            # breakpoint()
            result = app.run()
            assert "somemod" in sys.modules
            root = solara.RoutingProvider(children=[result], routes=app.routes, pathname="/")
            box, rc = solara.render(root, handle_error=False)
            assert rc.find(v.Card, children=["second"])
            somemod2 = sys.modules["somemod"]
            assert somemod1 is not somemod2
        finally:
            app.close()
            if "somemod" in sys.modules:
                del sys.modules["somemod"]
            reload.reloader.watched_modules.remove("somemod")


# def test_script_reload_component(tmpdir, kernel_context, extra_include_path, no_kernel_context):
#     import ipyvuetify as v

#     with extra_include_path(str(tmpdir)):
#         py_file = tmpdir / "test.py"

#         logger.info("writing files")
#         with open(py_file, "w") as f:
#             f.write("import reacton.ipyvuetify as v; Page = v.Btn\n")

#         app = AppScript(f"{py_file}")
#         try:
#             result = app.run()
#             assert result().component.widget == v.Btn
#             with open(py_file, "w") as f:
#                 f.write("import reacton.ipyvuetify as v; Page = v.Slider\n")
#             # wait for the event to trigger
#             reload.reloader.reload_event_next.wait()
#             # assert "somemod" not in sys.modules
#             # breakpoint()
#             result = app.run()
#             assert result().component.widget == v.Slider
#         finally:
#             app.close()


# def test_watch_module_import_error(tmpdir, kernel_context, extra_include_path, no_kernel_context):
#     import ipyvuetify as v

#     with extra_include_path(str(tmpdir)):
#         py_file = tmpdir / "test.py"
#         py_mod_file = tmpdir / "somemod2.py"

#         logger.info("writing files")
#         with open(py_mod_file, "w") as f:
#             f.write("import ipyvuetify as v; App = v.Btn.element\n")
#         with open(py_file, "w") as f:
#             f.write("import somemod2; app=somemod2.App\n")

#         logger.info("wrote files")

#         app = AppScript(f"{py_file}")
#         try:
#             result = app.run()
#             assert "somemod2" in sys.modules
#             assert "somemod2" in reload.reloader.watched_modules
#             assert result().component.widget == v.Btn

#             # syntax error
#             with open(py_mod_file, "w") as f:
#                 f.write("import ipyvuetify as v; App !%#$@= v.Card.element\n")
#             reload.reloader.reload_event_next.wait()
#             with pytest.raises(SyntaxError):
#                 result = app.run()

#             with open(py_mod_file, "w") as f:
#                 f.write("import ipyvuetify as v; App = v.Card.element\n")
#             reload.reloader.reload_event_next.wait()
#             result = app.run()
#             assert "somemod2" in sys.modules
#             assert result().component.widget == v.Card
#         finally:
#             app.close()
#             del sys.modules["somemod2"]
#             reload.reloader.watched_modules.remove("somemod2")
