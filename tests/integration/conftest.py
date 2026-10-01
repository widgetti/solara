import logging
import os
import sys
import threading
import traceback
from typing import Dict, List, Set

import playwright.sync_api
import pytest
from _pytest.tmpdir import tmppath_result_key

import solara.server.app
import solara.server.server
import solara.server.settings
from solara.server import reload
from solara.server.flask import ServerFlask
from solara.server.starlette import ServerStarlette
from solara.server.threaded import ServerBase

reload.reloader.start()
logger = logging.getLogger("solara-test.integration")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_teardown(item, nextitem):
    # workaround for pytest-retry (<=1.7.0) x pytest (8.x): a retried test that uses tmp_path
    # errors at teardown with KeyError on this stash key, turning a successfully retried flaky
    # test into a hard failure. Seed the entry so the tmp_path finalizer always finds it.
    item.stash.setdefault(tmppath_result_key, {})
    outcome = yield
    _dump_thread_stacks_on_timeout(outcome, item, "teardown")


@pytest.fixture(autouse=True)
def _leave_the_previous_page(request):
    # A test leaves the shared page_session on its app, and that app's kernel is then closed
    # (by the solara_app fixture, or by the next solara_app(...) switch). In development mode
    # the page reloads itself about 3 seconds after it loses its kernel, and on a slow runner
    # that reload interrupts the next test's page_session.goto. Leave the page first; this
    # also runs again before each pytest-retry attempt.
    if "page_session" in request.fixturenames:
        page_session = request.getfixturevalue("page_session")
        try:
            page_session.goto("about:blank")
        except playwright.sync_api.Error:
            # the reload can still interrupt this goto in a window of milliseconds, and
            # pytest-retry does not retry a setup error; the reloaded page reloads no more
            page_session.goto("about:blank")


# When a test times out waiting for a page, a server thread is often stuck (a hang or a
# deadlock), but the test only sees the timeout. Both test servers run in this process, so
# print the stack of every thread while they are still stuck. The checks wrap setup, call and
# teardown, because pytest-retry runs its retries through those hooks but not through
# pytest_runtest_makereport. One dump per test, for at most 3 tests per worker, is enough:
# the retries of a test, and the tests after a hang, usually time out too.
_tests_with_thread_stacks: Set[str] = set()


def _thread_stacks() -> str:
    names = {thread.ident: thread.name for thread in threading.enumerate()}
    # threads with the same stack (e.g. idle worker threads) are listed once
    threads_by_stack: Dict[str, List[str]] = {}
    for ident, frame in sys._current_frames().items():
        threads_by_stack.setdefault("".join(traceback.format_stack(frame)), []).append(f"{names.get(ident, '?')} ({ident})")
    return "\n".join(f"--- {len(threads)} thread(s): {', '.join(threads)} ---\n{stack}" for stack, threads in threads_by_stack.items())


def _write_to_stderr(text: str) -> None:
    # sys.stderr, not sys.__stderr__: xdist workers on Windows point fd 2 at devnull. The
    # Playwright driver can leave the stream non-blocking, and a non-blocking write drops what
    # does not fit in the pipe, so make it blocking for this write.
    fd, was_blocking = None, True
    try:
        fd = sys.stderr.fileno()
        was_blocking = os.get_blocking(fd)
        os.set_blocking(fd, True)
    except Exception:
        pass  # no file descriptor (the output is captured), or not supported (Windows)
    try:
        sys.stderr.write(text)
        sys.stderr.flush()
    finally:
        if fd is not None and not was_blocking:
            os.set_blocking(fd, False)


def _dump_thread_stacks_on_timeout(outcome, item, when: str) -> None:
    # the public Result.exception, read with getattr so it cannot raise
    if not isinstance(getattr(outcome, "exception", None), playwright.sync_api.TimeoutError):
        return
    if item.nodeid in _tests_with_thread_stacks or len(_tests_with_thread_stacks) >= 3:
        return
    _tests_with_thread_stacks.add(item.nodeid)
    title = f" thread stacks after a timeout in {item.nodeid} ({when}) "
    try:
        _write_to_stderr(f"{title:=^100}\n{_thread_stacks()}\n{'':=^100}\n")
    except Exception:
        pass  # a diagnostic must never change the result of a test


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_setup(item):
    outcome = yield
    _dump_thread_stacks_on_timeout(outcome, item, "setup")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item):
    outcome = yield
    _dump_thread_stacks_on_timeout(outcome, item, "call")


worker = os.environ.get("PYTEST_XDIST_WORKER", "gw0")
# each xdist worker runs its own flask and starlette server (see solara_server below), so workers
# need to be at least 2 ports apart. Ports up to 18770 are a valid callback for auth0, which keeps
# all ports valid with 2 workers.
TEST_PORT = int(os.environ.get("PORT", "18765")) + int(worker[2:]) * 3
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


# with xdist load scheduling, a parameterized session fixture is torn down and re-created on
# every flask<->starlette param switch. Cache the servers instead: it keeps each server alive
# (and its port, fixed per param - important for the auth0 callback range) for the whole
# session, and avoids racing a test's page navigation against a server restart
_servers: Dict[str, ServerBase] = {}


@pytest.fixture(params=SERVERS, scope="session")
def solara_server(request):
    name = request.param
    if name not in _servers:
        webserver = server_classes[name](TEST_PORT + SERVERS.index(name))
        webserver.serve_threaded()
        webserver.wait_until_serving()
        _servers[name] = webserver
    yield _servers[name]


@pytest.fixture(scope="session", autouse=True)
def _stop_solara_servers():
    yield
    for webserver in _servers.values():
        webserver.stop_serving()


@pytest.fixture()  # type: ignore # noqa
def page(page):  # noqa
    # on CI, it seems that the above context.set_default_timeout(timeout * 1000) does not apply to page
    # so we set it here again. Maybe in other situations the page is created early.. ?
    page.set_default_timeout(timeout * 1000)
    yield page
