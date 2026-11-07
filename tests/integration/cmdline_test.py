import subprocess
import time
from pathlib import Path

import playwright.sync_api

import solara.server.server
from solara.server.threaded import get_free_port

HERE = Path(__file__).parent


def test_run_widget(page_session: playwright.sync_api.Page):
    # an OS-assigned free port: this server does not need to be in the auth0 callback range,
    # and taking TEST_PORT + 1 collides with other xdist workers
    port = get_free_port()
    args = ["solara", "run", f"--port={port}", "--no-open", str(HERE / "app_widget.py") + ":button"]
    popen = subprocess.Popen(args, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
    host = "localhost"
    try:
        solara.server.server.wait_ready(f"http://{host}:{port}", timeout=15)
        page_session.wait_for_timeout(2000)  # on windows, the server is not ready yet?
        page_session.goto(f"http://localhost:{port}")
        page_session.locator("text=Clicked 0 times").click()
        page_session.locator("text=Clicked 1 times").click()
        page_session.locator("text=Clicked 2 times").wait_for()
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


def test_run_restart_dir_and_exclude(tmp_path: Path):
    watched = tmp_path / "watched"
    watched.mkdir()
    excluded_file = watched / "excluded.py"
    excluded_file.write_text("# before\n")
    watched_file = watched / "changed.py"
    watched_file.write_text("# before\n")
    app = tmp_path / "app.py"
    app.write_text('import solara\n\n\n@solara.component\ndef Page():\n    solara.Text("Hello")\n')

    port = get_free_port()
    args = [
        "solara",
        "run",
        f"--port={port}",
        "--no-open",
        "--no-check-version",
        "--auto-restart",
        "--log-level-uvicorn=info",
        f"--restart-dir={watched}",
        "--restart-exclude=excluded.py",
        str(app),
    ]
    output = tmp_path / "output.txt"
    with output.open("w") as output_file:
        popen = subprocess.Popen(args, cwd=tmp_path, stdout=output_file, stderr=subprocess.STDOUT)
        try:
            solara.server.server.wait_ready(f"http://localhost:{port}", timeout=30)
            # the excluded file changes first, so that a restart caused by it would be logged first
            excluded_file.write_text("# after\n")
            watched_file.write_text("# after\n")
            deadline = time.time() + 30
            while "changed.py" not in output.read_text() and time.time() < deadline:
                time.sleep(0.1)
        finally:
            # not kill: the reloader should get the chance to stop the server process it started
            popen.terminate()
            popen.wait(timeout=30)
    text = output.read_text()
    assert "changed.py" in text, text
    assert "excluded.py" not in text, text
