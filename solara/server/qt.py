import sys
from typing import List
import webbrowser
from qtpy.QtWidgets import QApplication
from qtpy.QtWebEngineWidgets import QWebEngineView
from qtpy.QtWebChannel import QWebChannel
from qtpy import QtCore, QtGui
import signal
from pathlib import Path

HERE = Path(__file__).parent


# setUrlRequestInterceptor, navigationRequested and acceptNavigationRequest
# all trigger the websocket to disconnect, so we need to block cross origin
# requests on the frontend/browser side by intercepting clicks on links

cross_origin_block_js = """
var script = document.createElement('script');
script.src = 'qrc:///qtwebchannel/qwebchannel.js';
document.head.appendChild(script);
script.onload = function() {
    new QWebChannel(qt.webChannelTransport, function(channel) {
        let py_callback = channel.objects.py_callback;

        document.addEventListener('click', function(event) {
            let target = event.target;
            while (target && target.tagName !== 'A') {
                target = target.parentNode;
            }

            if (target && target.tagName === 'A') {
                const linkOrigin = new URL(target.href).origin;
                const currentOrigin = window.location.origin;

                if (linkOrigin !== currentOrigin) {
                    event.preventDefault();
                    console.log("Blocked cross-origin navigation to:", target.href);
                    py_callback.open_link(target.href);  // Call Python method
                }
            }
        }, true);
    });
};
"""


class PyCallback(QtCore.QObject):
    @QtCore.Slot(str)
    def open_link(self, url):
        webbrowser.open(url)


class QWebEngineViewWithPopup(QWebEngineView):
    # keep a strong reference to all windows
    windows: List = []

    def __init__(self):
        super().__init__()
        self.page().newWindowRequested.connect(self.handle_new_window_request)

        # Set up WebChannel and py_callback object
        self.py_callback = PyCallback()
        self.channel = QWebChannel()
        self.channel.registerObject("py_callback", self.py_callback)
        self.page().setWebChannel(self.channel)

        self.loadFinished.connect(self._inject_javascript)

    def _inject_javascript(self, ok):
        self.page().runJavaScript(cross_origin_block_js)

    def handle_new_window_request(self, info):
        webview = QWebEngineViewWithPopup()
        geometry = info.requestedGeometry()
        webview.resize(geometry.width(), geometry.height())
        webview.setUrl(info.requestedUrl())
        webview.show()
        QWebEngineViewWithPopup.windows.append(webview)
        return webview


def run_qt(url):
    app = QApplication(["Solara App"])
    web = QWebEngineViewWithPopup()
    web.setUrl(QtCore.QUrl(url))
    web.resize(1024, 1024)
    web.show()

    app_name = "Solara"
    app.setApplicationDisplayName(app_name)
    app.setApplicationName(app_name)
    web.setWindowTitle(app_name)
    app.setWindowIcon(QtGui.QIcon(str(HERE.parent / "website/public/logo.svg")))
    if sys.platform.startswith("darwin"):
        # Set app name, if PyObjC is installed
        # Python 2 has PyObjC preinstalled
        # Python 3: pip3 install pyobjc-framework-Cocoa
        try:
            from Foundation import NSBundle

            bundle = NSBundle.mainBundle()
            if bundle:
                app_info = bundle.localizedInfoDictionary() or bundle.infoDictionary()
                if app_info is not None:
                    app_info["CFBundleName"] = app_name
                    app_info["CFBundleDisplayName"] = app_name
        except ModuleNotFoundError:
            pass

    # without this, ctrl-c does not work in the terminal
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    app.exec_()
