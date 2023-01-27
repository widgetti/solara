import subprocess
from pathlib import Path

import playwright.sync_api

import solara.server.server

from . import conftest

HERE = Path(__file__).parent


def test_run_widget(page_session: playwright.sync_api.Page):
    port = conftest.TEST_PORT
    conftest.TEST_PORT += 1
    args = ["solara", "run", f"--port={port}", "--no-open", str(HERE / "app_widget.py") + ":button"]
    popen = subprocess.Popen(args, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
    host = "localhost"
    try:
        solara.server.server.wait_ready(f"http://{host}:{port}", timeout=15)
        page_session.goto(f"http://localhost:{port}")
        page_session.locator("text=Clicked 0 times").click(timeout=5000)
        page_session.locator("text=Clicked 1 times").click(timeout=5000)
        page_session.locator("text=Clicked 2 times").wait_for(timeout=5000)
        popen.kill()
    except Exception as e:
        try:
            popen.kill()
        except:  # noqa
            pass
        outs, errs = popen.communicate(timeout=5)
        if errs:
            print("STDERR:")  # noqa
            print(errs.decode("utf-8"))  # noqa
        if outs:
            print("STDOUT:")  # noqa
            print(outs.decode("utf-8"))  # noqa
        if errs:
            raise ValueError("Expected no errors in solara server output") from e
        raise
