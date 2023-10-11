import threading
from pathlib import Path
from typing import Optional

import playwright.sync_api
from solara_enterprise import ssg

import solara
from solara.server import settings
from solara.server.kernel_context import VirtualKernelContext, get_current_context

HERE = Path(__file__).parent


text_ssg = "# SSG Test"
text_live = "# Live render"
context: Optional[VirtualKernelContext] = None


def set_value(x: str):
    return None


@solara.component
def SSG():
    global set_value
    global context
    value, set_value = solara.use_state(text_ssg)  # type: ignore
    context = get_current_context()
    with solara.HBox() as main:
        solara.Markdown(value)
        solara.Meta(name="description", property="og:description", content="My page description")
    return main


def test_ssg(page_session: playwright.sync_api.Page, solara_server, solara_app, tmpdir):
    global text
    global context

    settings.ssg.build_path = Path(tmpdir) / "build"
    # would be nice if we can get the headed/headless setting from pytest somehow
    # for now, disable the comment below to run in headed mode
    # settings.ssg.headed = True

    def run():
        # run in different thread, since playwright wants
        # its own event loop
        ssg.ssg_crawl(solara_server.base_url)

    with solara_app("tests.integration.ssg_test:SSG"):
        t = threading.Thread(target=run)
        t.start()
        t.join()
        path = settings.ssg.build_path / "index.html"
        assert path.exists()
        html = path.read_text()
        assert ">SSG Test</h1>" in html, "SSG did not render correctly"
        assert "og:description" in html, "SSG did not render meta correctly"
        assert "My page description" in html, "SSG did not render meta correctly"

        page_session.goto(solara_server.base_url)
        page_session.locator('h1:has-text("SSG Test")').wait_for()
        page_session.locator("#pre-rendered-html-present").wait_for(state="detached")
        assert context is not None
        # we need to use set_value with the right context, set_value is not aware of solara's context
        with context:
            set_value(text_live)
        page_session.locator("text=Live render").wait_for()
        context = None
