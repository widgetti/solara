from pathlib import Path

import playwright.sync_api
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

import solara
import solara.server.starlette
from solara.server import settings

HERE = Path(__file__).parent


@solara.component
def Page():
    solara.Markdown("Mounted in starlette")


def myroot(request: Request):
    return JSONResponse({"framework": "solara"})


starlette_routes = [
    Route("/", endpoint=myroot),
    Mount("/solara_mount/", routes=solara.server.starlette.routes),
]

starlette_app = Starlette(routes=starlette_routes)


def test_starlette_mount(page_session: playwright.sync_api.Page, solara_app, extra_include_path):
    settings.main.root_path = None
    settings.main.base_url = ""
    server = None
    try:
        # port=0 gives an OS-assigned free port: this server does not need to be in the auth0
        # callback range, and taking TEST_PORT + 1 collides with other xdist workers
        server = solara.server.starlette.ServerStarlette(port=0, starlette_app=starlette_app)
        server.serve_threaded()
        server.wait_until_serving()
        with extra_include_path(HERE), solara_app("starlette_test", init=False):
            page_session.goto(f"{server.base_url}/solara_mount/")
            page_session.locator("text=Mounted in starlette").wait_for()
    finally:
        # leave a dead page behind: its reconnect js can otherwise fire a late navigation that
        # interrupts the next test's page_session.goto
        page_session.goto("about:blank")
        if server is not None:
            server.stop_serving()
        settings.main.root_path = None
        settings.main.base_url = ""
