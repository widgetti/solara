import logging
import threading
import time
from typing import Optional

logger = logging.getLogger("solara.server.threaded")


class ServerBase(threading.Thread):
    name = "not set"

    def __init__(self, port: int, host: str = "localhost", **kwargs):
        self.port = port
        self.host = host
        self.base_url = f"http://{self.host}:{self.port}"

        self.kwargs = kwargs
        self.started = threading.Event()
        self.stopped = threading.Event()
        self.error: Optional[BaseException] = None
        super().__init__(name="test-server-thread", daemon=True)

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

    def wait_until_serving(self, timeout: float = 10):
        start = time.time()
        while time.time() < start + timeout:
            if self.has_started():
                time.sleep(0.1)  # give some time to really start
                return
            time.sleep(0.05)
        raise RuntimeError(f"Server at {self.base_url} does not seem to be running")

    def serve(self):
        raise NotImplementedError

    def mainloop(self):
        logger.info("serving at http://%s:%d" % (self.host, self.port))
        try:
            self.serve()
        except:  # noqa: E722
            logger.exception("Oops, server stopped unexpectedly")
            raise
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
