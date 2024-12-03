import logging
import os
from typing import Set

import playwright.sync_api
import pytest

import solara.server.app
import solara.server.server
import solara.server.settings
from solara.server import reload
from solara.server.flask import ServerFlask
from solara.server.starlette import ServerStarlette

reload.reloader.start()
logger = logging.getLogger("solara-test.integration")

worker = os.environ.get("PYTEST_XDIST_WORKER", "gw0")
TEST_PORT = int(os.environ.get("PORT", "18765")) + int(worker[2:])  # up to 18770 is a valid callback for auth0
SERVER = os.environ.get("SOLARA_SERVER")
if SERVER:
    SERVERS = [SERVER]
else:
    SERVERS = ["flask", "starlette"]


urls: Set[str] = set()

timeout = 18  # in seconds, slightly below the  --timeout=20 argument in integration.yml
# allow symlinks on solara+starlette
solara.server.settings.main.mode = "development"


@pytest.fixture(scope="session")
def url_checks():
    yield
    non_localhost = [url for url in urls if not url.startswith("http://localhost")]
    allow_list = [
        "https://user-images.githubusercontent.com",  # logo in readme
        "https://cdnjs.cloudflare.com/ajax/libs/emojione/2.2.7",  # emojione from markdown
        "https://images.unsplash.com",  # portal
        "https://miro.medium.com",  # portal
        "https://dabuttonfactory.com/",  # in markdown, probably temporary
    ]
    non_allow_urls = [url for url in non_localhost if not any(url.startswith(allow) for allow in allow_list)]
    if non_allow_urls:
        msg = "The following URLs were not allowed (non local host, and not in allow list):\n"
        msg += "\n".join(non_allow_urls)
        raise AssertionError(msg)


# see https://github.com/microsoft/playwright-pytest/issues/23
@pytest.fixture
def context(context: playwright.sync_api.BrowserContext, url_checks):
    context.set_default_timeout(timeout * 1000)

    def handle(route, request: playwright.sync_api.Request):
        urls.add(request.url)
        route.continue_()

    # context.route("**/*", handle)
    yield context


@pytest.fixture
def page(page: playwright.sync_api.Page):
    def log(msg):
        print("PAGE LOG:", msg.text)  # noqa
        logger.debug("PAGE LOG: %s", msg.text)

    page.on("console", log)
    return page


def _serve_flask_in_process(port, host):
    from solara.server.flask import app

    app.run(debug=False, port=port, host=host)


server_classes = {
    "flask": ServerFlask,
    "starlette": ServerStarlette,
}

# override the fixure, and also test with flask


@pytest.fixture(params=SERVERS, scope="session")
def solara_server(request):
    server_class = server_classes[request.param]
    global TEST_PORT
    webserver = server_class(TEST_PORT)
    TEST_PORT += 1

    try:
        webserver.serve_threaded()
        webserver.wait_until_serving()
        yield webserver
    finally:
        webserver.stop_serving()


@pytest.fixture()  # type: ignore # noqa
def page(page):  # noqa
    # on CI, it seems that the above context.set_default_timeout(timeout * 1000) does not apply to page
    # so we set it here again. Maybe in other situations the page is created early.. ?
    page.set_default_timeout(timeout * 1000)
    yield page
