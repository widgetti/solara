import json
import logging
import subprocess
import sys
import warnings
from pathlib import Path
from typing import Optional

import IPython.display
from IPython.core.interactiveshell import InteractiveShell
from IPython.display import display

import solara

HERE = Path(__file__).parent
logger = logging.getLogger(__name__)


def getcmdline(pid):
    # for linux
    if sys.platform == "linux":
        with open(f"/proc/{pid}/cmdline", "rb") as f:
            return f.read().split(b"\00")[0].decode("utf-8")
    elif sys.platform == "darwin":
        return subprocess.check_output(["ps", "-o", "command=", "-p", str(pid)]).split(b"\n")[0].split(b" ")[0].decode("utf-8")
    elif sys.platform == "win32":
        return subprocess.check_output(["wmic", "process", "get", "commandline", "/format:list"]).split(b"\n")[0].split(b" ")[0].decode("utf-8")
    else:
        raise ValueError(f"Unsupported platform: {sys.platform}")


def get_server_python_executable(silent: bool = False):
    servers = []
    try:
        from jupyter_server import serverapp

        servers += list(serverapp.list_running_servers())
    except ImportError:
        pass
    try:
        from notebook import notebookapp

        servers += list(notebookapp.list_running_servers())
    except ImportError:
        pass

    pythons = [getcmdline(server["pid"]) for server in servers]
    if len(pythons) == 0:
        python = sys.executable
        if not silent:
            warnings.warn("Could not find servers, we are assuming the server is running under Python executable: %s" % python)
    elif len(pythons) > 1:
        info = "\n\t".join(pythons)
        if sys.executable in pythons:
            python = sys.executable
        else:
            python = pythons[0]
            if not silent:
                warnings.warn("Found multiple find servers:\n%s\n" "We are assuming the server is running under Python executable: %s" % (info, python))
    else:
        python = pythons[0]
    return python


libraries_minimal = [
    {"python": "ipyvuetify", "classic": "jupyter-vuetify/extension", "lab": "jupyter-vuetify"},
    {"python": "ipyvue", "classic": "jupyter-vue/extension", "lab": "jupyter-vue"},
]

libraries_extra = [
    {"python": "bqplot", "classic": "bqplot/extension", "lab": "bqplot"},
    {"python": "ipyvolume", "classic": "ipyvolume/extension", "lab": "ipyvolume"},
    {"python": "ipywebrtc", "classic": "jupyter-webrtc", "lab": "jupyter-webrtc"},
    {"python": "ipyleaflet", "classic": "ipyleaflet/extension", "lab": "ipyleaflet"},
]


def check_jupyter(
    server_python: Optional[str] = None,
    silent: bool = False,
    libraries: list = libraries_minimal,
    libraries_extra: list = libraries_extra,
    force: bool = False,
    extra: bool = False,
):
    if solara._using_solara_server():
        # for the server we don't need to do this check
        return
    if not InteractiveShell.initialized():
        # also, in a normal python repr, we don't want to display anything
        return
    try:
        python_executable = server_python or get_server_python_executable(silent)
        if Path(python_executable).resolve() != Path(sys.executable).resolve() or force:
            libraries_json = json.dumps(libraries + (libraries_extra if extra else []))
            display(
                IPython.display.Javascript(
                    data="""
                    window.jupyter_python_executable = %r;
                    window.jupyter_widget_checks_silent = %s;
                    window.jupyter_widget_checks_libraries = %s;
                    """
                    % (python_executable, str(silent).lower(), libraries_json)
                )
            )
            display(IPython.display.HTML(filename=str(HERE / "checks.html")))
        else:
            if not silent:
                display(
                    IPython.display.HTML(
                        data="<div>Jupyter server is running under the same Python executable as your kernel, no need to check 👍."
                        "<br> <i>Run solara.check_jupyter(force=True) to force checking.</i></div>"
                    )
                )
    except Exception:
        logger.exception("Could not check jupyter-widgets extensions.")


check_jupyter(silent=True)
