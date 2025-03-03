import sys
import threading
from time import sleep
from pathlib import Path

import click
import os

# make sure you use pyside when distributing your app without having to use a GPL license
from qtpy.QtWidgets import QApplication
from qtpy.QtWebEngineWidgets import QWebEngineView
from qtpy import QtCore


HERE = Path(__file__).parent


@click.command()
@click.option(
    "--port",
    default=int(os.environ.get("PORT", 0)),
    help="Port to run the server on, 0 for a random free port",
)
def run(port: int):
    sys.path.append(str(HERE))
    os.environ["SOLARA_APP"] = "test_app"
    import test_app

    import solara.server.starlette

    server = solara.server.starlette.ServerStarlette(host="localhost", port=port)
    print(f"Starting server on {server.base_url}")
    server.serve_threaded()
    server.wait_until_serving()

    def test_success(value):
        print("test output", value)
        # calling app.quit seems to fail on windows and linux
        # possibly because we are in a non-qt-thread (solara)
        # app.quit()
        QtCore.QMetaObject.invokeMethod(app, "quit", QtCore.Qt.QueuedConnection)
        server.stop_serving()

    test_app.callback = test_success  # type: ignore

    failed = False

    def fail_guard():
        sleep(10)
        nonlocal failed
        print("failed")
        # similar as above
        QtCore.QMetaObject.invokeMethod(app, "quit", QtCore.Qt.QueuedConnection)
        failed = True

    app = QApplication([""])
    web = QWebEngineView()
    web.setUrl(QtCore.QUrl(server.base_url))
    web.show()

    threading.Thread(target=fail_guard, daemon=True).start()
    app.exec_()
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    run()
