from pathlib import Path

import uuid

import ipyreact
import playwright
import pytest
from packaging.version import Version

import solara
import solara.server.patch

solara.server.patch.patch()


HERE = Path(__file__).parent


test_js_code = """
import * as React from "react";

export default function({value, setValue, ...children}) {
    return React.createElement("button", {onClick: () => setValue(value + 1), children: `clicked ${value || 0}`})
}
"""
ipyreact.define_module("solara-test", code=test_js_code)


@solara.component
def Page():
    value = solara.use_reactive(0)
    ipyreact.ValueWidget.element(_module="solara-test", value=0, on_value=value.set)


@solara.component
def PageDefineDuringRun():
    ipyreact.define_module("solara-test-dynamic", code=test_js_code)
    value = solara.use_reactive(0)
    ipyreact.ValueWidget.element(_module="solara-test-dynamic", value=0, on_value=value.set)


@pytest.mark.parametrize("app", ["esm_test:Page", "esm_test:PageDefineDuringRun"])
def test_ipyreact(browser: playwright.sync_api.Browser, page_session: playwright.sync_api.Page, solara_server, solara_app, extra_include_path, app):
    with extra_include_path(HERE), solara_app(app):
        page_session.goto(solara_server.base_url)
        page_session.locator("text=clicked 0").first.click()
        page_session.locator("text=clicked 1").first.click()
        # now force a page reload / new kernel
        # which would fail if the module and import map widget
        # was shared between kernels
        page_session.goto(solara_server.base_url)
        page_session.locator("text=clicked 0").first.click()
        page_session.locator("text=clicked 1").first.click()


hot_module_code = """
import * as React from "react";

export function Label() {
    return React.createElement("div", {className: "hot-widget"}, "version %d");
};
"""

hot_app_code = """
from pathlib import Path

import ipyreact
import solara

HERE = Path(__file__).parent

ipyreact.define_module("hot-reload-module", HERE / "hot_module.js")


@solara.component
def Page():
    ipyreact.Widget.element(_module="hot-reload-module", _type="Label")
"""


@pytest.mark.skipif(
    Version(ipyreact.__version__) <= Version("0.5.0"),
    reason="needs the module hot reload frontend fixes (widgetti/ipyreact#79)",
)
def test_ipyreact_module_hot_reload(
    tmp_path, browser: playwright.sync_api.Browser, page_session: playwright.sync_api.Page, solara_server, solara_app, extra_include_path
):
    # define_module(Path) registers the bundle with the reloader: rewriting
    # the file must trigger an in-place reload, recreate the (closed) Module
    # widget and render the new code - no page refresh, no app file change.
    # unique module name: the app is imported once per parametrized instance
    # from a different tmp_path, but python caches by module name
    app_name = f"esm_hot_app_{uuid.uuid4().hex[:8]}"
    module_file = tmp_path / "hot_module.js"
    module_file.write_text(hot_module_code % 1)
    (tmp_path / f"{app_name}.py").write_text(hot_app_code)
    with extra_include_path(str(tmp_path)), solara_app(f"{app_name}:Page"):
        page_session.goto(solara_server.base_url)
        page_session.locator(".hot-widget >> text=version 1").wait_for()
        module_file.write_text(hot_module_code % 2)
        page_session.locator(".hot-widget >> text=version 2").wait_for()
