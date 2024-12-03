from pathlib import Path

import playwright.sync_api
from flask import Flask

import solara
import solara.server.flask

try:
    from . import conftest
except ImportError:
    pass


HERE = Path(__file__).parent


@solara.component
def Page():
    solara.Markdown("Mounted in flask")


flask_app = Flask(__name__)
flask_app.register_blueprint(solara.server.flask.blueprint, url_prefix="/solara_mount")


@flask_app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"


def test_flask_mount(page_session: playwright.sync_api.Page, solara_app, extra_include_path):
    port = conftest.TEST_PORT
    conftest.TEST_PORT += 1
    server = solara.server.flask.ServerFlask(port=port, flask_app=flask_app, url_prefix="/solara_mount")
    server.serve_threaded()
    server.wait_until_serving()
    with extra_include_path(HERE), solara_app("flask_test"):
        page_session.goto(f"{server.base_url}/solara_mount/")
        page_session.locator("text=Mounted in flask").wait_for()
        # assert page_session.text_content("p") == "Mounted in flask"
        # assert page_session.text_content("p") == "Mounted in flask"
