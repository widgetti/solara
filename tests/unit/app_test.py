# import logging
# import sys

# import pytest

# from solara.server import reload
# from solara.server.app import AppScript

# logger = logging.getLogger("solara.server.app_test")


# def test_watch_module_reload(tmpdir, app_context, extra_include_path):
#     import ipyvuetify as v

#     with extra_include_path(str(tmpdir)):
#         py_file = tmpdir / "test.py"
#         py_mod_file = tmpdir / "somemod.py"

#         logger.info("writing files")
#         with open(py_mod_file, "w") as f:
#             f.write("import ipyvuetify as v; App = v.Btn.element\n")
#         with open(py_file, "w") as f:
#             f.write("import somemod; app=somemod.App\n")

#         logger.info("wrote files")

#         app = AppScript(f"{py_file}")
#         try:
#             result = app.run()
#             assert "somemod" in sys.modules
#             assert "somemod" in reload.reloader.watched_modules
#             assert result().component.widget == v.Btn

#             # change depending module
#             with open(py_mod_file, "w") as f:
#                 f.write("import ipyvuetify as v; App = v.Card.element\n")
#             # wait for the event to trigger
#             reload.reloader.reload_event_next.wait()
#             # assert "somemod" not in sys.modules
#             result = app.run()
#             assert "somemod" in sys.modules
#             assert result().component.widget == v.Card
#         finally:
#             app.close()
#             del sys.modules["somemod"]
#             reload.reloader.watched_modules.remove("somemod")


# def test_watch_module_import_error(tmpdir, app_context, extra_include_path):
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
#             # import pdb

#             # pdb.set_trace()
#             result = app.run()
#             assert "somemod2" in sys.modules
#             assert "somemod2" in reload.reloader.watched_modules
#             assert result().component.widget == v.Btn

#             # syntax error
#             with open(py_mod_file, "w") as f:
#                 f.write("import ipyvuetify as v; App !%#$@= v.Card.element\n")
#             reload.reloader.reload_event_next.wait()
#             # # assert "somemod" not in sys.modules
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
