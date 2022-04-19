import contextlib
import logging
import sys
import threading
import time
from typing import Union

import pytest

import solara.server.app
import solara.server.server
from solara.server import reload
from solara.server.fastapi import app as app_starlette

logger = logging.getLogger("solara-test.integration")

TEST_PORT = 18765


# see https://github.com/microsoft/playwright-pytest/issues/23
@pytest.fixture
def context(context):
    context.set_default_timeout(3000)
    yield context


class Server(threading.Thread):
    def __init__(self, port, host="localhost", **kwargs):
        self.port = port
        self.host = host
        self.base_url = f"http://{self.host}:{self.port}"

        self.kwargs = kwargs
        self.started = threading.Event()
        self.stopped = threading.Event()
        self.error = None
        super().__init__(name="fastapi-thread")
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
        url = f"http://{self.host}:{self.port}/"
        for n in range(10):
            # try:
            #     response = requests.get(url)
            # except requests.exceptions.ConnectionError:
            #     pass
            # else:
            #     if response.status_code == 200:
            #         return
            if self.server.started:
                return
            time.sleep(0.05)
        else:
            raise RuntimeError(f"Server at {url} does not seem to be running")

    def mainloop(self):
        logger.info("serving at http://%s:%d" % (self.host, self.port))

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
        try:
            self.server.run()
        except:  # noqa: E722
            logger.exception("Oops, server stopped unexpectedly")
        finally:
            self.stopped.set()

    def stop_serving(self):
        logger.debug("stopping server")
        print("STOP IT!")
        self.server.should_exit = True
        self.server.lifespan.should_exit = True
        self.stopped.wait(10)
        if not self.stopped.is_set():
            logger.error("stopping server failed")
        else:
            logger.debug("stopped server")


@pytest.fixture()  # scope="module")
def solara_server():
    global TEST_PORT
    webserver = Server(TEST_PORT)
    webserver.serve_threaded()
    webserver.wait_until_serving()
    try:
        yield webserver
    finally:
        webserver.stop_serving()
        TEST_PORT += 1


@pytest.fixture()
def solara_app(solara_server):
    @contextlib.contextmanager
    def run(app: Union[solara.server.app.AppScript, str]):
        solara.server.server.solara_app.close()
        if isinstance(app, str):
            app = solara.server.app.AppScript(app)
        solara.server.server.solara_app = app
        try:
            yield
        finally:
            if app.type == solara.server.app.AppType.MODULE:
                del sys.modules[app.name]
                reload.reloader.watched_modules.remove(app.name)

            app.close()

    return run
