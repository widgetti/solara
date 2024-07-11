import threading
from pathlib import Path

import playwright
import playwright.sync_api
import pytest
import reacton.ipywidgets as w
import requests

import solara
import solara.server.server
from solara.server import settings

HERE = Path(__file__).parent


def test_large_cookie(browser: playwright.sync_api.Browser, page_session: playwright.sync_api.Page, solara_server, solara_app):
    with solara_app("solara.website.pages"):
        port = solara_server.port
        # more than 8kb of cookies
        for i in range(9):
            browser.contexts[0].add_cookies([{"name": f"a_{i}", "value": "a" * 1024, "url": f"http://localhost:{port}"}])
        page_session.goto(solara_server.base_url)
        page_session.locator("text=Examples").first.click()


def test_docs_basics(page_session: playwright.sync_api.Page, solara_server, solara_app):
    with solara_app("solara.website.pages"):
        page_session.goto(solara_server.base_url)
        page_session.get_by_role("link", name="Documentation").click()

        page_session.locator("text=Search the Solara Documentation").wait_for()
        page_session.locator(".docs-card", has_text="Examples").first.click()
        page_session.locator(".v-card >> text=Calculator").first.click()
        page_session.locator("text=+/-").wait_for()
        page_session.screenshot(path="tmp/screenshot_calculator.png")

        page_session.locator("text=Libraries").first.click()
        page_session.locator("text=Bqplot").first.click()
        page_session.locator("text=Exponent").wait_for()
        page_session.screenshot(path="tmp/screenshot_bqplot.png")

        page_session.locator("text=Visualization").first.click()
        page_session.locator("text=Scatter plot using Plotly").first.click()
        page_session.locator("text=This example shows how to use Plotly").wait_for()
        page_session.screenshot(path="tmp/screenshot_plotly.png")

        page_session.locator("text=Plotly Image Annotator").first.click()
        page_session.locator("text=how to annotate images with").first.wait_for()


def test_docs_routes(page_session: playwright.sync_api.Page, solara_server, solara_app):
    with solara_app("solara.website.pages"):
        page_session.goto(solara_server.base_url + "/documentation/getting_started/tutorials/streamlit")
        page_session.locator("text=Streamlit example").first.wait_for()

        page_session.goto(solara_server.base_url + "/documentation/api/routing/use_route/")
        page_session.locator("text=Go to fruit/banana").wait_for()

        page_session.goto(solara_server.base_url + "/documentation/api/routing/use_route/fruit/fruit/banana")
        page_session.locator("text=You chose banana").wait_for()

        page_session.locator("text=Wrong fruit").click()
        page_session.locator("text=Fruit not found, go to banana").wait_for()


@solara.component
def ClickButton():
    count, set_count = solara.use_state(0)
    if not isinstance(count, int):
        print("oops, state issue?")  # noqa
        count = 0

    def on_click():
        set_count(count + 1)

    return solara.Button(f"Clicked: {count}", on_click=on_click)


@solara.component
def ThreadTest():
    label, set_label = solara.use_state("initial")
    use_thread, set_use_thread = solara.use_state(False)

    def from_thread():
        set_label("from thread")

    def start_thread():
        if use_thread:
            thread = threading.Thread(target=from_thread)
            thread.start()
            return thread.join

    solara.use_side_effect(start_thread, [use_thread])
    # we need to trigger creating a new widget, to make sure we
    # invoke a solara.server.app.get_current_context
    if label == "initial":
        return w.Button(description=label, on_click=lambda: set_use_thread(True))
    else:
        return w.Label(value=label)


def test_from_thread(page_session: playwright.sync_api.Page, solara_server, solara_app, extra_include_path):
    with extra_include_path(HERE), solara_app("server_test:ThreadTest"):
        page_session.goto(solara_server.base_url)
        el = page_session.locator(".jupyter-widgets")
        assert el.text_content() == "initial"
        page_session.wait_for_timeout(500)
        el.click()
        page_session.locator("text=from thread").wait_for()


def test_state(page_session: playwright.sync_api.Page, solara_server, solara_app, extra_include_path):
    with extra_include_path(HERE), solara_app("server_test:ClickButton"):
        page_session.goto(solara_server.base_url)
        page_session.locator("text=Clicked: 0").click()
        page_session.locator("text=Clicked: 1").click()
        # refresh...
        page_session.goto(solara_server.base_url)
        # and state should NOT be restored
        page_session.locator("text=Clicked: 0").wait_for()


def test_from_thread_two_users(browser: playwright.sync_api.Browser, solara_server, solara_app, extra_include_path):
    with extra_include_path(HERE), solara_app("server_test:ThreadTest"):
        context1 = browser.new_context()
        page1 = context1.new_page()
        context2 = browser.new_context()
        page2 = context2.new_page()

        page1.goto(solara_server.base_url)

        el1 = page1.locator(".jupyter-widgets")
        assert el1.text_content() == "initial"

        page2.goto(solara_server.base_url)
        el2 = page2.locator(".jupyter-widgets")
        assert el2.text_content() == "initial"

        page1.wait_for_timeout(500)
        page1.wait_for_timeout(500)

        el1.click()
        page1.locator("text=from thread").wait_for()

        page2.wait_for_timeout(500)
        assert el2.text_content() == "initial"

        el2.click()
        page2.locator("text=from thread").wait_for()
        page1.close()
        page2.close()


@solara.component
def StaticPage():
    return w.Label(value="Hello world")


def test_run_in_iframe(page_session: playwright.sync_api.Page, solara_server, solara_app, extra_include_path):
    page_session.context.clear_cookies()
    with extra_include_path(HERE), solara_app("server_test:StaticPage"):
        page_session.set_content(
            f"""
            <html>
            <body>
                <iframe name="main" src="{solara_server.base_url}"></iframe>
            </body>
            </html>
        """
        )

        iframe = page_session.frame("main")
        assert iframe is not None
        el = iframe.locator(".jupyter-widgets")
        assert el.text_content() == "Hello world"


@solara.component
def ClickTaskButton():
    count = solara.use_reactive(0)

    @solara.lab.use_task(dependencies=None)
    def on_click():
        count.value += 1

    return solara.Button(f"Clicked: {count}", on_click=on_click)


def test_kernel_asyncio(browser: playwright.sync_api.Browser, solara_server, solara_app, extra_include_path, request):
    if request.node.callspec.params["solara_server"] != "starlette":
        pytest.skip("Async is only supported on starlette.")
        return
    # ClickTaskButton also tests the use of tasks
    try:
        threaded = solara.server.settings.kernel.threaded
        solara.server.settings.kernel.threaded = False
        with extra_include_path(HERE), solara_app("server_test:ClickTaskButton"):
            context1 = browser.new_context()
            page1 = context1.new_page()
            page1.goto(solara_server.base_url)
            page1.locator("text=Clicked: 0").click()
            page1.locator("text=Clicked: 1").click()
            context2 = browser.new_context()
            page2 = context2.new_page()
            page2.goto(solara_server.base_url)
            page2.locator("text=Clicked: 0").click()
            page2.locator("text=Clicked: 1").click()
            page1.locator("text=Clicked: 2").wait_for()
            page2.locator("text=Clicked: 2").wait_for()
    finally:
        page1.close()
        page2.close()
        context1.close()
        context2.close()
        solara.server.settings.kernel.threaded = threaded


def test_cdn_secure(solara_server, solara_app, extra_include_path):
    cdn_url = solara_server.base_url + "/_solara/cdn"
    assert solara.settings.assets.proxy

    with extra_include_path(HERE), solara_app("server_test:ClickButton"):
        url = cdn_url + "/vue-grid-layout@1.0.2/dist/vue-grid-layout.min.js"
        response = requests.get(url)
        assert response.status_code == 200
        # create a file in /share/solara
        test_file = settings.assets.proxy_cache_dir.parent / "not-allowed"
        test_file.write_text("test")
        url = cdn_url + "/..%2fnot-allowed"
        response = requests.get(url)
        assert response.status_code == 404


def test_nbextension_secure(solara_server, solara_app, extra_include_path):
    nbextensions_url = solara_server.base_url + "/static/nbextensions"
    nbextensions_directories = [k for k in solara.server.server.nbextensions_directories if k.exists()]
    assert nbextensions_directories, "we should at least test one directory"
    nbextensions_directory = nbextensions_directories[0]

    with extra_include_path(HERE), solara_app("server_test:ClickButton"):
        url = nbextensions_url + "/jupyter-vuetify/nodeps.js"
        response = requests.get(url)
        assert response.status_code == 200
        test_file = nbextensions_directory.parent / "not-allowed"
        test_file.write_text("test")
        url = nbextensions_url + "/..%2fnot-allowed"
        response = requests.get(url)
        assert response.status_code == 404

        url = nbextensions_url + "/foo/..%2f..%2fnot-allowed"
        response = requests.get(url)
        assert response.status_code == 404


def test_assets_secure(solara_server, solara_app, extra_include_path):
    assets_url = solara_server.base_url + "/static/assets"
    assets_directory = solara.server.server.solara_static.parent / "assets"

    with extra_include_path(HERE), solara_app("server_test:ClickButton"):
        url = assets_url + "/theme.js"
        response = requests.get(url)
        assert response.status_code == 200
        test_file = assets_directory.parent / "__init__.py"
        assert test_file.exists()
        url = assets_url + "/..%2f__init__.py"
        response = requests.get(url)
        assert response.status_code == 404

        url = assets_url + "/foo/..%2f..%2f__init__.py"
        response = requests.get(url)
        assert response.status_code == 404


def test_public_secure(solara_server, solara_app, extra_include_path):
    public_url = solara_server.base_url + "/static/public"

    with solara_app(str(HERE / "apps/secure/app.py")):
        apps = list(solara.server.app.apps.values())
        assert len(apps) == 1
        app = apps[0]
        public_directory = app.directory.parent / "public"
        url = public_url + "/test.txt"
        response = requests.get(url)
        assert response.status_code == 200
        test_file = public_directory.parent / "not-allowed"
        assert test_file.exists()
        url = public_url + "/..%2fnot-allowed"
        response = requests.get(url)
        assert response.status_code == 404

        url = public_url + "/foo/..%2f..%2fnot-allowed"
        response = requests.get(url)
        assert response.status_code == 404


def test_static_secure(solara_server, solara_app, extra_include_path):
    static_url = solara_server.base_url + "/static"
    static_directory = solara.server.server.solara_static

    with extra_include_path(HERE), solara_app("server_test:ClickButton"):
        url = static_url + "/main.js"
        response = requests.get(url)
        assert response.status_code == 200
        test_file = static_directory.parent / "__init__.py"
        assert test_file.exists()
        url = static_url + "/..%2f__init__.py"
        response = requests.get(url)
        assert response.status_code == 404

        url = static_url + "/foo/..%2f..%2f__init__.py"
        response = requests.get(url)
        assert response.status_code == 404
