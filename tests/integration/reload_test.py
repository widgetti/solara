import contextlib
import logging

# import subprocess
from pathlib import Path

# import playwright.sync_api

# import solara.server.server

# from . import conftest

app_path = Path(__file__).parent / "testapp.py"

logger = logging.getLogger("solara-test.integration.reload_test")


HERE = Path(__file__).parent


@contextlib.contextmanager
def append(text):
    with app_path.open() as f:
        content = f.read()
    try:
        with app_path.open("w") as f:
            f.write(content)
            f.write(text)
        yield
    finally:
        with app_path.open("w") as f:
            f.write(content)


@contextlib.contextmanager
def replace(path, text):
    with path.open() as f:
        content = f.read()
    try:
        with path.open("w") as f:
            f.write(text)
        yield
    finally:
        with path.open("w") as f:
            f.write(content)


# button_code = """
# @solara.component
# def ButtonClick():
#     clicks, set_clicks = solara.use_state(Clicks(0))
#     return rw.Button(description=f"!!! {clicks.value} times", on_click=lambda: set_clicks(Clicks(clicks.value + 1)))


# app = ButtonClick()
# """


# def test_reload_with_pickle(page_session: playwright.sync_api.Page):
#     port = conftest.TEST_PORT + 1000
#     conftest.TEST_PORT += 1
#     args = ["solara", "run", f"--port={port}", "--no-open", "tests.integration.testapp:app", "--log-level=debug"]
#     popen = subprocess.Popen(args, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
#     host = "localhost"
#     try:
#         solara.server.server.wait_ready(f"http://{host}:{port}", timeout=10)
#         page_session.goto(f"http://localhost:{port}")
#         page_session.locator("text=Clicked 0 times").click(timeout=5000)
#         page_session.locator("text=Clicked 1 times").click(timeout=5000)
#         page_session.locator("text=Clicked 2 times").wait_for(timeout=5000)
#         page_session.wait_for_timeout(1000)
#         with append(button_code):
#             page_session.locator("text=!!! 0 times").click(timeout=5000)
#             page_session.locator("text=!!! 1 times").click(timeout=5000)
#         popen.kill()
#     except Exception as e:
#         try:
#             popen.kill()
#         except:  # noqa
#             pass
#         outs, errs = popen.communicate(timeout=5)
#         if errs:
#             print("STDERR:")  # noqa
#             print(errs.decode("utf-8"))  # noqa
#         if outs:
#             print("STDOUT:")  # noqa
#             print(outs.decode("utf-8"))  # noqa
#         if errs:
#             raise ValueError("Expected no errors in solara server output") from e
#         raise


# the following tests are flakey on CI

# def test_reload_syntax_error(page_session: playwright.sync_api.Page, solara_server, solara_app, extra_include_path):
#     with extra_include_path(app_path.parent), solara_app("testapp:ButtonClick"):
#         # use as module, otherwise pickle will not work
#         page_session.goto(solara_server.base_url)
#         assert page_session.title() == "Solara ☀️"
#         page_session.locator("text=Clicked 0 times").click()
#         page_session.locator("text=Clicked 1 times").click()

#         with append("\n$%#$%"):
#             reload.reloader.reload_event_next.wait()
#             # page_session.locator("text=Clicked 2 times").click()
#             page_session.locator("text=SyntaxError").wait_for()
#         reload.reloader.reload_event_next.wait()
#         page_session.locator("text=Clicked 2 times").click()
#         page_session.locator("text=Clicked 3 times").wait_for()


# def test_reload_change(page_session: playwright.sync_api.Page, solara_server, solara_app, extra_include_path):
#     with extra_include_path(app_path.parent), solara_app("testapp:app"):
#         logger.info("test_reload_many:run app")
#         page_session.goto(solara_server.base_url)
#         # assert page_session.title() == "Solara ☀️"
#         page_session.locator("text=Clicked 0 times").click()
#         page_session.locator("text=Clicked 1 times").click()
#         with append(button_code):
#             reload.reloader.reload_event_next.wait()
#             # page_session.locator("text=Clicked 2 times").click()
#             # page_session.locator("text=SyntaxError").wait_for()
#             page_session.locator("text=!!! 0 times").click()


# def test_reload_many(page_session: playwright.sync_api.Page, solara_server, solara_app, extra_include_path):
#     with extra_include_path(app_path.parent), solara_app("testapp:app"):
#         logger.info("test_reload_many:run app")
#         # use as module, otherwise pickle will not work
#         page_session.goto(solara_server.base_url)
#         page_session.locator("text=Clicked 0 times").click()
#         page_session.locator("text=Clicked 1 times").click()

#         logger.info("test_reload_many:Touch app 1st time")
#         app_path.touch()
#         reload.reloader.reload_event_next.wait()
#         page_session.locator("text=Clicked 2 times").click()
#         page_session.locator("text=Clicked 3 times").wait_for(state="visible")

#         logger.info("test_reload_many:Touch app 2nd time")
#         app_path.touch()
#         reload.reloader.reload_event_next.wait()
#         page_session.locator("text=Clicked 3 times").click()
#         page_session.locator("text=Clicked 4 times").wait_for(state="visible")


# def test_reload_vue(page_session: playwright.sync_api.Page, solara_server, solara_app, extra_include_path):
#     with extra_include_path(app_path.parent), solara_app("testapp:VueTestApp"):
#         page_session.goto(solara_server.base_url)
#         page_session.locator("text=foobar").wait_for()

#         vuecode = """
# <template>
#   <div>RELOADED</div>
# </template>
#         """
#         vuepath = Path(__file__).parent / "test.vue"
#         with replace(vuepath, vuecode):
#             page_session.locator("text=RELOADED").wait_for()
#         page_session.locator("text=foobar").wait_for()
