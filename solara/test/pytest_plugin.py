import contextlib
import inspect
import json
import logging
import os
import shlex
import subprocess
import sys
import textwrap
import threading
import typing
from io import BytesIO
from pathlib import Path
from typing import Any, Callable, Dict, Generator, List, Union

import ipywidgets as widgets
import pytest
import requests
from IPython.display import display

import solara.server.app
import solara.server.server
import solara.server.settings
from solara.server import reload
from solara.server.starlette import ServerStarlette
from solara.server.threaded import ServerBase

if typing.TYPE_CHECKING:
    import playwright.sync_api


logger = logging.getLogger("solara.pytest_plugin")

TEST_PORT = int(os.environ.get("PORT", "18765")) + 100  # do not interfere with the solara integration tests
TIMEOUT = float(os.environ.get("SOLARA_PW_TIMEOUT", "18"))


@pytest.fixture(scope="session")
def solara_server(request):
    global TEST_PORT
    webserver = ServerStarlette(TEST_PORT)
    TEST_PORT += 1

    try:
        webserver.serve_threaded()
        webserver.wait_until_serving()
        yield webserver
    finally:
        webserver.stop_serving()


@pytest.fixture(scope="session")
def context_session(
    browser: "playwright.sync_api.Browser",
    browser_context_args: Dict,
    pytestconfig: Any,
    request: pytest.FixtureRequest,
) -> Generator["playwright.sync_api.BrowserContext", None, None]:
    from playwright.sync_api import Error, Page
    from pytest_playwright.pytest_playwright import _build_artifact_test_folder
    from slugify import slugify  # type: ignore

    pages: List[Page] = []
    context = browser.new_context(**browser_context_args)
    context.on("page", lambda page: pages.append(page))

    tracing_option = pytestconfig.getoption("--tracing")
    capture_trace = tracing_option in ["on", "retain-on-failure"]
    if capture_trace:
        context.tracing.start(
            title=slugify(request.node.nodeid),
            screenshots=True,
            snapshots=True,
            sources=True,
        )

    # decrease timeout from 30s to 10s
    context.set_default_timeout(TIMEOUT * 1000)
    yield context

    # If request.node is missing rep_call, then some error happened during execution
    # that prevented teardown, but should still be counted as a failure
    failed = request.node.rep_call.failed if hasattr(request.node, "rep_call") else True

    if capture_trace:
        retain_trace = tracing_option == "on" or (failed and tracing_option == "retain-on-failure")
        if retain_trace:
            trace_path = _build_artifact_test_folder(pytestconfig, request, "trace.zip")
            context.tracing.stop(path=trace_path)
        else:
            context.tracing.stop()

    screenshot_option = pytestconfig.getoption("--screenshot")
    capture_screenshot = screenshot_option == "on" or (failed and screenshot_option == "only-on-failure")
    if capture_screenshot:
        for index, page in enumerate(pages):
            human_readable_status = "failed" if failed else "finished"
            screenshot_path = _build_artifact_test_folder(pytestconfig, request, f"test-{human_readable_status}-{index+1}.png")
            try:
                page.screenshot(timeout=5000, path=screenshot_path)
            except Error:
                pass

    context.close()

    video_option = pytestconfig.getoption("--video")
    preserve_video = video_option == "on" or (failed and video_option == "retain-on-failure")
    if preserve_video:
        for page in pages:
            video = page.video
            if not video:
                continue
            try:
                video_path = video.path()
                file_name = os.path.basename(video_path)
                video.save_as(path=_build_artifact_test_folder(pytestconfig, request, file_name))
            except Error:
                # Silent catch empty videos.
                pass


# page fixture that keeps open all the time, is faster
@pytest.fixture(scope="session")
def page_session(context_session: "playwright.sync_api.BrowserContext"):
    page = context_session.new_page()
    yield page
    page.close()


@pytest.fixture()
def solara_app(solara_server):
    @contextlib.contextmanager
    def run(app: Union[solara.server.app.AppScript, str]):
        if "__default__" in solara.server.app.apps:
            solara.server.app.apps["__default__"].close()
        if isinstance(app, str):
            app = solara.server.app.AppScript(app)
        solara.server.app.apps["__default__"] = app
        try:
            yield
        finally:
            if app.type == solara.server.app.AppType.MODULE:
                if app.name in sys.modules and app.name.startswith("tests.integration.testapp"):
                    del sys.modules[app.name]
                if app.name in reload.reloader.watched_modules:
                    reload.reloader.watched_modules.remove(app.name)

            app.close()

    return run


run_event = threading.Event()
run_calls = 0


@solara.component
def SyncWrapper():
    global run_calls
    import reacton.ipywidgets as w

    run_calls += 1
    run_event.set()
    return w.VBox(children=[w.HTML(value="Test in solara"), w.VBox()])


@pytest.fixture()
def solara_test(solara_server, solara_app, page_session: "playwright.sync_api.Page"):
    global run_calls
    with solara_app("solara.test.pytest_plugin:SyncWrapper"):
        page_session.goto(solara_server.base_url)
        run_event.wait()
        assert run_calls == 1
        keys = list(solara.server.app.contexts)
        assert len(keys) == 1, "expected only one context, got %s" % keys
        context = solara.server.app.contexts[keys[0]]
        with context:
            test_output_warmup = widgets.Output()
            test_output = widgets.Output()
            try:
                page_session.locator("text=Test in solara").wait_for()
                context.container.children[0].children[1].children[1].children = [test_output_warmup]  # type: ignore
                with test_output_warmup:
                    warmup()
                    button = page_session.locator(".solara-warmup-widget")
                    button.wait_for()
                    page_session.evaluate("document.fonts.ready")
                    button.click()
                    button.wait_for(state="detached")
                    page_session.evaluate("document.fonts.ready")
                context.container.children[0].children[1].children[1].children = [test_output]  # type: ignore
                with test_output:
                    yield
            finally:
                test_output.close()
                run_event.clear()
                test_output = None
                run_calls = 0


class ServerVoila(ServerBase):
    popen = None

    def __init__(self, notebook_path, port: int, host: str = "localhost", **kwargs):
        self.notebook_path = notebook_path
        super().__init__(port, host)

    def has_started(self):
        try:
            return requests.get(self.base_url).status_code // 100 in [2, 3]
        except requests.exceptions.ConnectionError:
            return False

    def signal_stop(self):
        if self.popen is None:
            return
        self.popen.terminate()
        self.popen.kill()

    def serve(self):
        if self.has_started():
            raise RuntimeError("Jupyter server already running, use lsof -i :{self.port} to find the process and kill it")
        cmd = (
            "voila --no-browser --VoilaTest.log_level=DEBUG --Voila.port_retries=0 --VoilaExecutor.timeout=240"
            f" --Voila.port={self.port} --show_tracebacks=True {self.notebook_path} --enable_nbextensions=True"
        )
        logger.info(f"Starting Voila server at {self.base_url} with command {cmd}")
        args = shlex.split(cmd)
        self.popen = subprocess.Popen(args, shell=False, stdout=sys.stdout, stderr=sys.stderr, stdin=None)
        self.started.set()


class ServerJupyter(ServerBase):
    popen = None

    def __init__(self, notebook_path, port: int, host: str = "localhost", **kwargs):
        self.notebook_path = notebook_path
        super().__init__(port, host)

    def has_started(self):
        try:
            return requests.get(self.base_url).status_code // 100 in [2, 3]
        except requests.exceptions.ConnectionError:
            return False

    def signal_stop(self):
        if self.popen is None:
            return
        self.popen.terminate()
        self.popen.kill()

    def serve(self):
        if self.has_started():
            raise RuntimeError(f"Jupyter server already running, use lsof -i :{self.port} to find the process and kill it")
        cmd = f'jupyter lab --port={self.port} --no-browser --ServerApp.token="" --port-retries=0 {self.notebook_path}'
        logger.info(f"Starting Jupyter (lab) server at {self.base_url} with command {cmd}")
        args = shlex.split(cmd)
        self.popen = subprocess.Popen(args, shell=False, stdout=sys.stdout, stderr=sys.stderr, stdin=None)
        self.started.set()


@pytest.fixture(scope="session")
def voila_server(notebook_path):
    global TEST_PORT
    port = TEST_PORT
    TEST_PORT += 1
    write_notebook(["print('hello')"], notebook_path)
    server = ServerVoila(notebook_path, port)
    try:
        server.serve_threaded()
        server.wait_until_serving()
        yield server
    finally:
        server.stop_serving()


@pytest.fixture(scope="session")
def jupyter_server(notebook_path):
    global TEST_PORT
    port = TEST_PORT
    TEST_PORT += 1
    write_notebook(["print('hello')"], notebook_path)
    server = ServerJupyter(notebook_path, port)
    try:
        server.serve_threaded()
        server.wait_until_serving()
        yield server
    finally:
        server.stop_serving()


def code_from_function(f) -> str:
    lines = inspect.getsourcelines(f)[0]
    lines = lines[1:]
    return textwrap.dedent("".join(lines))


def write_notebook(codes: List[str], path: str):
    notebook = {
        "cells": [{"cell_type": "code", "execution_count": None, "id": "df77670d", "metadata": {}, "outputs": [], "source": [code]} for code in codes],
        "metadata": {
            "kernelspec": {"display_name": "Python 3 (ipykernel)", "language": "python", "name": "python3"},
            "language_info": {
                "codemirror_mode": {"name": "ipython", "version": 3},
                "file_extension": ".py",
                "mimetype": "text/x-python",
                "name": "python",
                "nbconvert_exporter": "python",
                "pygments_lexer": "ipython3",
                "version": "3.9.16",
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }

    with open(path, "w") as file:
        json.dump(notebook, file)


@pytest.fixture(scope="session")
def notebook_path(tmp_path_factory):
    path = tmp_path_factory.mktemp("notebooks") / "notebook.ipynb"
    yield str(path)


def warmup():
    import ipyvuetify as v

    # give it a scope so we do not collide with the user's code
    def scoped():
        button = v.Btn(children=["Warmup js/css/fonts", v.Icon(children=["mdi-check"])], class_="solara-warmup-widget")
        container = v.Container(
            children=[button],
            class_="ma-2 snapshot-container",
        )

        def remove_button(*ignore):
            container.children = []
            container.style_ = "display: none"

        button.on_event("click", remove_button)
        return container

    display(scoped())


def create_runner_voila(voila_server, notebook_path, page_session: "playwright.sync_api.Page"):
    count = 0
    base_url = voila_server.base_url

    def run(f: Callable):
        nonlocal count
        path = Path(f.__code__.co_filename)
        cwd = str(path.parent)
        code_setup = f"""
import os
os.chdir({cwd!r})
        \n"""
        write_notebook([code_setup, code_from_function(warmup), code_from_function(f)], notebook_path)
        page_session.goto(base_url + f"?v={count}")
        button = page_session.locator(".solara-warmup-widget")
        button.wait_for()
        page_session.evaluate("document.fonts.ready")
        button.click()
        button.wait_for(state="detached")
        page_session.evaluate("document.fonts.ready")
        count += 1

    return run


def create_runner_jupyter_lab(jupyter_server, notebook_path, page_session: "playwright.sync_api.Page"):
    count = 0
    base_url = jupyter_server.base_url

    def run(f: Callable):
        nonlocal count
        path = Path(f.__code__.co_filename)
        cwd = str(path.parent)
        code_setup = f"""
import os
os.chdir({cwd!r})
import ipyvuetify as v;
v.Btn(children=['Warmup js/css/fonts', v.Icon(children=["mdi-check"])], class_="solara-warmup-widget")
        \n"""
        write_notebook([code_setup, code_from_function(f)], notebook_path)
        page_session.goto(base_url + f"/lab/workspaces/solara-test/tree/notebook.ipynb?reset&v={count}")
        page_session.locator('css=[data-command="runmenu:run"]').wait_for()
        # close the file browser tab, it does not give a consistent width each time
        # which leads to fractional pixel x, which causes the screenshot to be different
        # by 1 pixel
        # first make sure the page is loaded
        page_session.locator('css=[data-id="filebrowser"]').wait_for()
        page_session.locator('css=[data-command="filebrowser:create-main-launcher"]').wait_for()
        # close
        page_session.locator('css=[data-id="filebrowser"]').click()
        # make sure it is closed
        page_session.locator('css=[data-command="filebrowser:create-main-launcher"]').wait_for(state="hidden")

        page_session.locator('button:has-text("No Kernel")').wait_for(state="detached")
        page_session.locator('css=[data-status="idle"]').wait_for()
        page_session.locator('css=[data-command="runmenu:run"]').click()
        page_session.locator(".solara-warmup-widget").wait_for()
        page_session.evaluate("document.fonts.ready")
        page_session.locator('css=[data-command="runmenu:run"]').click()
        count += 1

    return run


def create_runner_jupyter_notebook(jupyter_server, notebook_path, page_session: "playwright.sync_api.Page"):
    count = 0
    base_url = jupyter_server.base_url

    def run(f: Callable):
        nonlocal count
        path = Path(f.__code__.co_filename)
        cwd = str(path.parent)
        code_setup = f"""
import os
os.chdir({cwd!r})
import ipyvuetify as v;
v.Btn(children=['Warmup js/css/fonts', v.Icon(children=["mdi-check"])], class_="solara-warmup-widget")
        \n"""
        write_notebook([code_setup, code_from_function(f)], notebook_path)
        page_session.goto(base_url + f"/notebooks/notebook.ipynb?v={count}")
        page_session.locator("text=Kernel starting, please wait...").wait_for(state="detached")
        page_session.locator("Kernel Ready").wait_for(state="detached")
        page_session.locator('css=[data-jupyter-action="jupyter-notebook:run-cell-and-select-next"]').click()
        page_session.locator(".solara-warmup-widget").wait_for()
        page_session.evaluate("document.fonts.ready")
        page_session.locator('css=[data-jupyter-action="jupyter-notebook:run-cell-and-select-next"]').click()
        count += 1

    return run


def create_runner_solara(solara_test, solara_server, page_session: "playwright.sync_api.Page"):
    count = 0

    def run(f: Callable):
        nonlocal count
        path = Path(f.__code__.co_filename)
        cwd = str(path.parent)
        current_dir = os.getcwd()
        os.chdir(cwd)
        import sys

        sys.path.append(cwd)
        try:
            f()
        finally:
            os.chdir(current_dir)
            sys.path.remove(cwd)
        count += 1

    return run


@pytest.fixture(scope="session")
def ipywidgets_runner_voila(voila_server, notebook_path, page_session: "playwright.sync_api.Page"):
    if "voila" not in runners:
        return None
    return create_runner_voila(voila_server, notebook_path, page_session)


@pytest.fixture(scope="session")
def ipywidgets_runner_jupyter_lab(jupyter_server, notebook_path, page_session: "playwright.sync_api.Page"):
    if "jupyter_lab" not in runners:
        return None
    return create_runner_jupyter_lab(jupyter_server, notebook_path, page_session)


@pytest.fixture(scope="session")
def ipywidgets_runner_jupyter_notebook(jupyter_server, notebook_path, page_session: "playwright.sync_api.Page"):
    if "jupyter_notebook" not in runners:
        return None
    return create_runner_jupyter_notebook(jupyter_server, notebook_path, page_session)


@pytest.fixture()
def ipywidgets_runner_solara(solara_test, solara_server, page_session: "playwright.sync_api.Page"):
    if "solara" not in runners:
        return None
    return create_runner_solara(solara_test, solara_server, page_session)


runners = os.environ.get("SOLARA_TEST_RUNNERS", "solara,voila,jupyter_lab,jupyter_notebook").split(",")


@pytest.fixture(params=runners)
def ipywidgets_runner(
    ipywidgets_runner_jupyter_notebook,
    ipywidgets_runner_jupyter_lab,
    ipywidgets_runner_voila,
    ipywidgets_runner_solara,
    request,
):
    runner = request.param
    name = f"ipywidgets_runner_{runner}"
    return locals()[name]


@pytest.fixture(scope="session")
def solara_snapshots_directory(request: Any) -> Path:
    path = Path(request.config.rootpath) / "tests" / "ui" / "snapshots"
    if not path.exists():
        path.mkdir(exist_ok=True, parents=True)
    return path


def compare_default(reference, result, threshold=0.1):
    from PIL import Image
    from pixelmatch.contrib.PIL import pixelmatch

    difference = Image.new("RGB", reference.size)
    diff = pixelmatch(reference, result, difference, threshold=threshold)
    return diff, difference


@pytest.fixture
def assert_solara_snapshot(pytestconfig: Any, request: Any, browser_name: str, solara_snapshots_directory) -> Callable:
    from PIL import Image

    testname = f"{str(Path(request.node.name))}".replace("[", "-").replace("]", "").replace(" ", "-").replace(",", "-")
    directory = solara_snapshots_directory / request.node.location[0]
    output_dir = Path(pytestconfig.getoption("--output")) / request.node.location[0]
    if not directory.exists():
        directory.mkdir(exist_ok=True, parents=True)
    if not output_dir.exists():
        output_dir.mkdir(exist_ok=True, parents=True)

    def assert_implementation(
        image: bytes,
        compare: Callable = compare_default,
        testname=testname,
        format="{prefix}{testname}-{platform}{postfix}-{type}.png",
        prefix="",
        postfix="",
    ):
        update_snapshot = pytestconfig.getoption("--solara-update-snapshots")
        format_kwargs = dict(testname=testname, platform=sys.platform, browser=browser_name, prefix=prefix, postfix=postfix)
        path_reference = directory / format.format(**format_kwargs, type="reference").format(**format_kwargs)
        path_reference_output = output_dir / format.format(**format_kwargs, type="reference").format(**format_kwargs)
        path_previous = output_dir / format.format(**format_kwargs, type="previous").format(**format_kwargs)
        path_diff = output_dir / format.format(**format_kwargs, type="diff").format(**format_kwargs)
        if not path_reference.exists():
            if update_snapshot:
                path_reference.write_bytes(image)
            else:
                # CI run, store the reference, but fail
                path_reference_output.write_bytes(image)
                raise AssertionError(
                    f'Snapshot {path_reference} did not exist, file written. Run `cp "{path_reference_output}" "{path_reference}"` '
                    "Commit this file and rerun the CI. Or run with --solara-update-snapshots to update it."
                )
        else:
            if update_snapshot:
                path_reference.write_bytes(image)
            else:
                reference = Image.open(path_reference)
                result = Image.open(BytesIO(image))
                difference = None

                def write():
                    if update_snapshot:
                        path_reference.write_bytes(image)
                    else:
                        # CI run, update the reference in the output dir, and store the previous run next to it
                        path_reference_output.write_bytes(image)
                        reference.save(path_previous)
                        if difference is not None:
                            difference.save(path_diff)

                # the error msg of the default compare is not very helpful
                if reference.size != result.size:
                    write()
                    raise AssertionError(
                        f"Snapshot {path_reference} has a different size than the result {reference.size} != {result.size}."
                        f'Run `cp "{path_reference_output}" "{path_reference}"` Commit this file and rerun the CI. '
                        "Or run with --solara-update-snapshots to update it."
                    )
                diff, difference = compare(reference, result)
                if diff > 0:
                    write()
                    raise AssertionError(
                        f'Snapshot {path_reference} does not match, Run `cp "{path_reference_output}" "{path_reference}"` Commit this file and rerun the CI. '
                        "Or run with --solara-update-snapshots to update it."
                    )

    return assert_implementation


def pytest_addoption(parser: Any) -> None:
    group = parser.getgroup("solara", "Solara")
    group.addoption(
        "--solara-update-snapshots",
        action="store_true",
        default=False,
        help="Do not compare, but store the snapshots.",
    )
    group.addoption(
        "--solara-update-snapshots-ci",
        action="store_true",
        default=False,
        help="On compare failure, store to the reference image. Useful for running in CI and downloading the snapshots.",
    )
