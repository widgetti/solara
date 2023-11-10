import os
import sys

import playwright.sync_api
import pytest

pytest.importorskip("solara_enterprise")

from solara_enterprise.auth import get_logout_url  # noqa

from solara.server import settings  # noqa

if sys.version_info[:2] <= (3, 6):
    pytest.skip("Test requires python 3.7 or higher", allow_module_level=True)


@pytest.mark.skipif(not bool(os.environ.get("AUTH0_PASSWORD")), reason="AUTH0_PASSWORD not set")
def test_oauth_from_app_auth0(page_session: playwright.sync_api.Page, solara_server, solara_app):
    with solara_app("solara.website.pages"):
        settings.main.base_url = ""
        settings.oauth.client_id = settings.AUTH0_TEST_CLIENT_ID
        settings.oauth.client_secret = settings.AUTH0_TEST_CLIENT_SECRET
        settings.oauth.api_base_url = settings.AUTH0_TEST_API_BASE_URL
        settings.oauth.logout_path = settings.AUTH0_LOGOUT_PATH
        page_session.goto(solara_server.base_url + "/examples/general/login_oauth")
        page_session.locator("_vue=v-btn >> text=Login").click()
        page_session.locator('css=input[name="username"]').fill(os.environ["AUTH0_USERNAME"])
        page_session.locator('css=input[name="password"]').fill(os.environ["AUTH0_PASSWORD"])
        page_session.locator('css=button[name="action"]').nth(-1).click()
        page_session.locator("_vue=v-btn >> text=Logout").click()
        # do another round, we've
        page_session.locator("_vue=v-btn >> text=Login").click()
        page_session.locator('css=input[name="username"]').fill(os.environ["AUTH0_USERNAME"])
        page_session.locator('css=input[name="password"]').fill(os.environ["AUTH0_PASSWORD"])
        page_session.locator('css=button[name="action"]').nth(-1).click()
        page_session.locator("_vue=v-btn >> text=Logout").click()
        page_session.locator("_vue=v-btn >> text=Login").wait_for()
        page_session.locator("_vue=v-btn >> text=Login").wait_for()


@pytest.mark.skipif(not bool(os.environ.get("FIEF_PASSWORD")), reason="FIEF_PASSWORD not set")
def test_oauth_from_app_fief(page_session: playwright.sync_api.Page, solara_server, solara_app):
    with solara_app("solara.website.pages"):
        settings.main.base_url = ""
        settings.oauth.client_id = settings.FIEF_TEST_CLIENT_ID
        settings.oauth.client_secret = settings.FIEF_TEST_CLIENT_SECRET
        settings.oauth.api_base_url = settings.FIEF_TEST_API_BASE_URL
        settings.oauth.logout_path = settings.FIEF_LOGOUT_PATH
        page_session.goto(solara_server.base_url + "/examples/general/login_oauth")
        page_session.locator("_vue=v-btn >> text=Login").click()
        page_session.locator('css=input[name="email"]').fill(os.environ["FIEF_USERNAME"])
        page_session.locator('css=input[name="password"]').fill(os.environ["FIEF_PASSWORD"])
        page_session.locator('css=button[type="submit"]').click()
        page_session.locator("_vue=v-btn >> text=Logout").click()
        page_session.locator("_vue=v-btn >> text=Login").wait_for()


@pytest.mark.skipif(not bool(os.environ.get("AUTH0_PASSWORD")), reason="AUTH0_PASSWORD not set")
def test_oauth_private(page_session: playwright.sync_api.Page, solara_server, solara_app):
    settings.oauth.private = True
    try:
        with solara_app("solara.website.pages"):
            settings.main.base_url = ""
            settings.oauth.client_id = settings.AUTH0_TEST_CLIENT_ID
            settings.oauth.client_secret = settings.AUTH0_TEST_CLIENT_SECRET
            settings.oauth.api_base_url = settings.AUTH0_TEST_API_BASE_URL
            settings.oauth.logout_path = settings.AUTH0_LOGOUT_PATH

            response = page_session.goto(solara_server.base_url + "/static/public/beach.jpeg?cache=off")
            assert response is not None
            assert response.status == 401
            assert page_session.goto(solara_server.base_url + "/invalid_url").status == 401
            page_session.goto(solara_server.base_url + "/api/style")
            page_session.locator('css=input[name="username"]').fill(os.environ["AUTH0_USERNAME"])
            page_session.locator('css=input[name="password"]').fill(os.environ["AUTH0_PASSWORD"])
            page_session.locator('css=button[name="action"]').nth(-1).click()
            page_session.locator("text=Add a custom piece of CSS").wait_for()
            response = page_session.goto(solara_server.base_url + "/static/public/beach.jpeg")
            assert response is not None
            assert str(response.status)[0] == "2"  # check 2xx
            page_session.goto(get_logout_url("/api/style"))
            page_session.locator('css=input[name="username"]').fill(os.environ["AUTH0_USERNAME"])
            response = page_session.goto(solara_server.base_url + "/static/public/beach.jpeg?cache=off")
            assert response is not None
            assert response.status == 401
    finally:
        settings.oauth.private = False
