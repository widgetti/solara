import sys
from pathlib import Path

import ipyreact
import playwright
import pytest

import solara
import solara.server.patch

solara.server.patch.patch()


HERE = Path(__file__).parent


ipyreact.define_module(
    "solara-test",
    """
import * as React from "react";

export default function({value, setValue, ...children}) {
return React.createElement("button", {onClick: () => setValue(value + 1), children: `clicked ${value || 0}`})
}
""",
)


@solara.component
def Page():
    value = solara.use_reactive(0)
    ipyreact.ValueWidget.element(_module="solara-test", value=0, on_value=value.set)


@pytest.mark.skipif(sys.version_info < (3, 7, 0), reason="ipyreact requires python 3.7 or higher")
def test_ipyreact(browser: playwright.sync_api.Browser, page_session: playwright.sync_api.Page, solara_server, solara_app, extra_include_path):
    with extra_include_path(HERE), solara_app("esm_test:Page"):
        page_session.goto(solara_server.base_url)
        page_session.locator("text=clicked 0").first.click()
        page_session.locator("text=clicked 1").first.click()
        # now force a page reload / new kernel
        # which would fail if the module and import map widget
        # was shared between kernels
        page_session.goto(solara_server.base_url)
        page_session.locator("text=clicked 0").first.click()
        page_session.locator("text=clicked 1").first.click()
