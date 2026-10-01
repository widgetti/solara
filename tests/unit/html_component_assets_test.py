import asyncio

from starlette.requests import Request

from solara.components.html_component_assets import get_component_asset, register_component_asset


def test_registered_asset_is_content_addressed_and_typed():
    css_name = register_component_asset(":host { color: red; }", "css")
    assert register_component_asset(":host { color: red; }", "css") == css_name
    assert css_name.endswith(".css")
    assert get_component_asset(css_name) == (":host { color: red; }", "text/css")

    script_name = register_component_asset("export function mount() {}", "js")
    assert script_name.endswith(".js")
    assert get_component_asset(script_name) == ("export function mount() {}", "text/javascript")


def test_asset_lookup_rejects_unregistered_and_non_hash_paths():
    assert get_component_asset("../../other.js") is None
    assert get_component_asset("0" * 64 + ".js") is None
    assert get_component_asset("0" * 64 + ".html") is None


def test_starlette_asset_response_has_module_mime_and_cache_headers():
    from solara.server.starlette import html_component_asset

    name = register_component_asset("export const answer = 42;", "js")
    request = Request({"type": "http", "method": "GET", "path": "/static/html-components/" + name, "headers": [], "path_params": {"name": name}})
    response = asyncio.run(html_component_asset(request))

    assert response.body == b"export const answer = 42;"
    assert response.media_type == "text/javascript"
    assert "immutable" in response.headers["Cache-Control"]
    assert response.headers["X-Content-Type-Options"] == "nosniff"


def test_flask_asset_route_is_available():
    from solara.server.flask import app

    name = register_component_asset(":host { display: block; }", "css")
    response = app.test_client().get("/static/html-components/" + name)

    assert response.status_code == 200
    assert response.data == b":host { display: block; }"
    assert response.mimetype == "text/css"
    assert "immutable" in response.headers["Cache-Control"]
