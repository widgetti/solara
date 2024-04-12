from pathlib import Path
from typing import List
import requests


import solara.server.starlette
import solara.server.settings
import contextlib

import playwright.sync_api
from playwright.sync_api import expect


HERE = Path(__file__).parent


@contextlib.contextmanager
def extra_assets(locations: List[str]):
    prev = solara.server.settings.assets.extra_locations
    solara.server.settings.assets.extra_locations = locations
    try:
        yield
    finally:
        solara.server.settings.assets.extra_locations = prev


def test_assets_extra(solara_server):
    response = requests.get(f"{solara_server.base_url}/static/assets/common.js")
    assert response.status_code == 404

    with extra_assets([str(HERE / "assets" / "assets1")]):
        response = requests.get(f"{solara_server.base_url}/static/assets/common.js")
        assert response.status_code == 200
        assert response.text == "content1\n"
        response = requests.get(f"{solara_server.base_url}/static/assets/unique1.js")
        assert response.status_code == 200
        response = requests.get(f"{solara_server.base_url}/static/assets/unique2.js")
        assert response.status_code == 404

        response = requests.get(f"{solara_server.base_url}/static/assets/custom.js")
        assert response.status_code == 200
        assert response.text == "/* not empty */\n"

    with extra_assets([str(HERE / "assets" / "assets2")]):
        response = requests.get(f"{solara_server.base_url}/static/assets/common.js")
        assert response.status_code == 200
        assert response.text == "content2\n"
        response = requests.get(f"{solara_server.base_url}/static/assets/unique1.js")
        assert response.status_code == 404
        response = requests.get(f"{solara_server.base_url}/static/assets/unique2.js")
        assert response.status_code == 200

        response = requests.get(f"{solara_server.base_url}/static/assets/custom.js")
        assert response.status_code == 200
        assert response.text == "var a = 1;\n"

    with extra_assets([str(HERE / "assets" / "assets1"), str(HERE / "assets" / "assets2")]):
        response = requests.get(f"{solara_server.base_url}/static/assets/common.js")
        assert response.status_code == 200
        assert response.text == "content1\n"
        response = requests.get(f"{solara_server.base_url}/static/assets/unique1.js")
        assert response.status_code == 200
        response = requests.get(f"{solara_server.base_url}/static/assets/unique2.js")
        assert response.status_code == 200


def test_api_style(page_session: playwright.sync_api.Page, solara_server, solara_app):
    # this test is added because the include css macro in the jinja template may embed the
    # css, which also requires respecting the extra assets directories
    with solara_app("solara.website.pages.documentation.components.input.button"), extra_assets(
        [str(HERE / "assets" / "assets1"), str(HERE / "assets" / "assets2")]
    ):
        page_session.goto(solara_server.base_url)
        button = page_session.locator("text=Clicked 0 times")
        button.first.wait_for()
        expect(button).to_have_css("color", "rgb(255, 0, 0)")
