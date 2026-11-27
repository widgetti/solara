from pathlib import Path

import playwright.sync_api
from starlette.applications import Starlette
from starlette.routing import Mount

import solara
import solara.server.starlette
from solara.server import settings

HERE = Path(__file__).parent


@solara.component
def Home():
    solara.Markdown("This is home")
    with solara.Link("/page-a"):
        solara.Button("Link to page a")


@solara.component
def PageA():
    router = solara.use_router()
    solara.Markdown("This is page a, query: " + str(router.search))
    solara.Markdown("[Relative link to page b](./page-b)")
    solara.Markdown("[Absolute link to home](/)")
    solara.Button("Add query", on_click=lambda: router.push("/page-a?fruit=kiwi"))


@solara.component
def PageB():
    solara.Markdown("This is page b")


routes = [
    solara.Route("/", component=Home),
    solara.Route("page-a", children=[solara.Route("/", component=PageA), solara.Route("page-b", component=PageB)]),
]

starlette_app = Starlette(routes=[Mount("/solara_mount/", routes=solara.server.starlette.routes)])


def test_navigation_keeps_root_path(page_session: playwright.sync_api.Page, solara_app, extra_include_path):
    settings.main.root_path = None
    settings.main.base_url = ""
    server = None
    try:
        server = solara.server.starlette.ServerStarlette(port=0, starlette_app=starlette_app)
        server.serve_threaded()
        server.wait_until_serving()
        root = f"{server.base_url}/solara_mount"
        with extra_include_path(HERE), solara_app("root_path_test", init=False):
            page_session.goto(f"{root}/")
            page_session.locator("text=This is home").wait_for()

            # what the browser uses for e.g. opening the link in a new tab
            link = page_session.locator("a:has-text('Link to page a')")
            assert link.get_attribute("href") == "/solara_mount/page-a"
            link.click()
            page_session.locator("text=This is page a, query: None").wait_for()
            assert page_session.url == f"{root}/page-a"

            # the url should still lead to the same page
            page_session.reload()
            page_session.locator("text=This is page a, query: None").wait_for()

            page_session.locator("button:has-text('Add query')").click()
            page_session.locator("text=This is page a, query: fruit=kiwi").wait_for()
            assert page_session.url == f"{root}/page-a?fruit=kiwi"
            page_session.go_back()
            page_session.locator("text=This is page a, query: None").wait_for()
            assert page_session.url == f"{root}/page-a"

            page_session.locator("text=Relative link to page b").click()
            page_session.locator("text=This is page b").wait_for()
            assert page_session.url == f"{root}/page-a/page-b"
            page_session.go_back()
            page_session.locator("text=This is page a").wait_for()

            page_session.locator("text=Absolute link to home").click()
            page_session.locator("text=This is home").wait_for()
            assert page_session.url == f"{root}/"
    finally:
        # leave a dead page behind: its reconnect js can otherwise fire a late navigation that
        # interrupts the next test's page_session.goto
        page_session.goto("about:blank")
        if server is not None:
            server.stop_serving()
        settings.main.root_path = None
        settings.main.base_url = ""
