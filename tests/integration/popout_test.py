from pathlib import Path
from typing import cast

import ipyvue
import playwright
import playwright.sync_api
import traitlets
from reacton.core import _RenderContext

import solara
import solara.server
import solara.server.settings
from solara.server import kernel_context

HERE = Path(__file__).parent


@solara.component
def TwoTexts():
    with solara.Div(classes=["solara-test-div"]):
        solara.Text("AAA")
        solara.Text("BBB")


def test_popout(page_session: playwright.sync_api.Page, solara_server, solara_app, extra_include_path):
    with extra_include_path(HERE), solara_app("popout_test:TwoTexts"):
        page_session.goto(solara_server.base_url + "?solara-no-close-beacon")
        el = page_session.locator("text=AAA")
        assert el.text_content() == "AAA"
        contexts = list(kernel_context.contexts.values())
        assert len(contexts) == 1
        context = contexts[0]
        kernel_id = context.id
        rc = cast(_RenderContext, context.app_object)
        widget = rc.find(children=["BBB"]).widget
        model_id = widget._model_id

        # we should not lose the context, it should be kept alive
        page_session.goto("about:blank")
        page_session.wait_for_timeout(100)
        contexts = list(kernel_context.contexts.values())
        assert len(contexts) == 1

        page_session.goto(solara_server.base_url + f"?kernelid={kernel_id}&modelid={model_id}")
        page_session.locator("text=BBB").wait_for()
        page_session.locator("text=AAA").wait_for(state="detached")

        cull_timeout_previous = solara.server.settings.kernel.cull_timeout
        try:
            solara.server.settings.kernel.cull_timeout = "0s"
            page_session.goto("about:blank")
            page_session.wait_for_timeout(1000)
            contexts = list(kernel_context.contexts.values())
            assert len(contexts) == 0
        finally:
            solara.server.settings.kernel.cull_timeout = cull_timeout_previous


class PlainTemplate(ipyvue.VueTemplate):
    template = traitlets.Unicode("<template><div>plain-template-content</div></template>").tag(sync=True)


@solara.component
def PlainVueRoot():
    root = solara.use_memo(lambda: ipyvue.Html(tag="div", class_="popout-plain-root", children=["plain-root-text", PlainTemplate()]), [])
    solara.display(root)


def test_popout_plain_ipyvue_root(page_session: playwright.sync_api.Page, solara_server, solara_app, extra_include_path):
    # a popout (Jupyter, ipypopout) of a plain ipyvue widget: attached as a Lumino widget, as in Jupyter
    with extra_include_path(HERE), solara_app("popout_test:PlainVueRoot"):
        page_session.goto(solara_server.base_url + "?solara-no-close-beacon")
        page_session.locator("text=plain-template-content").wait_for()
        (context,) = kernel_context.contexts.values()
        (root,) = (widget for widget in context.widgets.values() if isinstance(widget, ipyvue.Html) and widget.class_ == "popout-plain-root")
        model_id = root._model_id

        page_session.goto(solara_server.base_url + f"?kernelid={context.id}&modelid={model_id}")
        page_session.locator("text=plain-template-content").wait_for()
        page_session.locator("text=plain-root-text").wait_for()
        assert page_session.evaluate("document.querySelector('.popout-plain-root').closest('.lm-Widget') !== null")

        cull_timeout_previous = solara.server.settings.kernel.cull_timeout
        try:
            solara.server.settings.kernel.cull_timeout = "0s"
            page_session.goto("about:blank")
            page_session.wait_for_timeout(1000)
        finally:
            solara.server.settings.kernel.cull_timeout = cull_timeout_previous
