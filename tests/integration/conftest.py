import contextlib
import logging
import os
import sys
import threading
import time
from http.server import HTTPServer
from typing import Optional, Set, Union

import playwright.sync_api
import pytest
import uvicorn.server

import solara.server.app
import solara.server.server
import solara.server.settings
from solara.server import reload
from solara.server.starlette import app as app_starlette

logger = logging.getLogger("solara-test.integration")

worker = os.environ.get("PYTEST_XDIST_WORKER", "gw0")
TEST_PORT = 18765 + 100 + int(worker[2:])
SERVER = os.environ.get("SOLARA_SERVER")
if SERVER:
    SERVERS = [SERVER]
else:
    SERVERS = ["flask", "starlette"]


urls: Set[str] = set()


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
    context.set_default_timeout(50000)

    def handle(route, request: playwright.sync_api.Request):
        urls.add(request.url)
        route.continue_()

    # context.route("**/*", handle)
    yield context


class ServerBase(threading.Thread):
    def __init__(self, port: int, host: str = "localhost", **kwargs):
        self.port = port
        self.host = host
        self.base_url = f"http://{self.host}:{self.port}"

        self.kwargs = kwargs
        self.started = threading.Event()
        self.stopped = threading.Event()
        self.error: Optional[BaseException] = None
        self.server = None
        super().__init__(name="test-server-thread")
        self.setDaemon(True)

    def run(self):
        try:
            logger.info("Starting main loop")
            self.mainloop()
        except BaseException as e:  # noqa
            self.error = e
            self.started.set()
            logger.exception("Issue starting server")

    def serve_threaded(self):
        logger.debug("start thread")
        self.start()
        logger.debug("wait for thread to run")
        self.started.wait()
        if self.error:
            raise self.error

    def wait_until_serving(self):
        for n in range(30):
            if self.has_started():
                time.sleep(0.1)  # give some time to really start
                return
            time.sleep(0.05)
        else:
            raise RuntimeError(f"Server at {self.base_url} does not seem to be running")

    def serve(self):
        raise NotImplementedError

    def mainloop(self):
        logger.info("serving at http://%s:%d" % (self.host, self.port))
        try:
            self.serve()
        except:  # noqa: E722
            logger.exception("Oops, server stopped unexpectedly")
        finally:
            self.stopped.set()

    def stop_serving(self):
        logger.debug("stopping server")
        self.signal_stop()
        self.stopped.wait(10)
        if not self.stopped.is_set():
            logger.error("stopping server failed")
        else:
            logger.debug("stopped server")

    def signal_stop(self):
        pass

    def has_started(self) -> bool:
        return False


class ServerStarlette(ServerBase):
    server: uvicorn.server.Server

    def has_started(self):
        return self.server.started

    def signal_stop(self):
        self.server.should_exit = True
        # this cause uvicorn to not wait for background tasks, e.g.:
        # <Task pending name='Task-55'
        #  coro=<WebSocketProtocol.run_asgi() running at
        #  /.../uvicorn/protocols/websockets/websockets_impl.py:184>
        # wait_for=<Future pending cb=[<TaskWakeupMethWrapper object at 0x16896aa00>()]>
        # cb=[WebSocketProtocol.on_task_complete()]>
        self.server.force_exit = True
        self.server.lifespan.should_exit = True

    def serve(self):

        from uvicorn.config import Config
        from uvicorn.server import Server

        if sys.version_info[:2] < (3, 7):
            # make python 3.6 work
            import asyncio

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # uvloop will trigger a: RuntimeError: There is no current event loop in thread 'fastapi-thread'
        config = Config(app_starlette, host=self.host, port=self.port, **self.kwargs, loop="asyncio")
        self.server = Server(config=config)
        self.started.set()
        self.server.run()


def _serve_flask_in_process(port, host):
    from solara.server.flask import app

    app.run(debug=False, port=port, host=host)


class ServerFlask(ServerBase):
    def has_started(self):
        import socket

        s = socket.socket()
        try:
            s.connect((self.host, self.port))
        except ConnectionRefusedError:
            return False
        return True

    def signal_stop(self):
        assert isinstance(self.server, HTTPServer)
        self.server.shutdown()  # type: ignore

    def serve(self):
        from werkzeug.serving import make_server

        from solara.server.flask import app

        self.server = make_server(self.host, self.port, app, threaded=True)  # type: ignore
        assert isinstance(self.server, HTTPServer)
        self.started.set()
        self.server.serve_forever(poll_interval=0.05)  # type: ignore


server_classes = {
    "flask": ServerFlask,
    "starlette": ServerStarlette,
}


@pytest.fixture(params=SERVERS)
def solara_server(request):
    server_class = server_classes[request.param]
    global TEST_PORT
    webserver = server_class(TEST_PORT)

    try:
        webserver.serve_threaded()
        webserver.wait_until_serving()
        yield webserver
    finally:
        webserver.stop_serving()
        TEST_PORT += 1


@pytest.fixture()
def solara_app(solara_server):
    @contextlib.contextmanager
    def run(app: Union[solara.server.app.AppScript, str]):
        solara.server.app.apps["__default__"].close()
        if isinstance(app, str):
            app = solara.server.app.AppScript(app)
        solara.server.app.apps["__default__"] = app
        try:
            yield
        finally:
            if app.type == solara.server.app.AppType.MODULE:
                if app.name in sys.modules:
                    del sys.modules[app.name]
                if app.name in reload.reloader.watched_modules:
                    reload.reloader.watched_modules.remove(app.name)

            app.close()

    return run
