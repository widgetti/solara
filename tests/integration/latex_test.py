import ipywidgets as widgets
import playwright.sync_api
import pytest
from IPython.display import display

from .conftest import SERVERS

widgets_version_major = int(widgets.__version__.split(".")[0])
widgets_postfix = f"-ipywidgets-{widgets_version_major}"


def test_widget_latex_solara(solara_test, page_session: playwright.sync_api.Page, assert_solara_snapshot, request):
    if request.node.callspec.params["solara_server"] != SERVERS[0]:
        pytest.skip("No need to run this test for all servers.")
    # we tried a FloatSlider before, but that seems to give unstable images (handle moves around randomly)
    label = widgets.Label(value=r"$E \sim mc^2$")
    label.add_class("test-class-latex")
    container = widgets.VBox([label], layout={"width": "200px", "height": "100px"})
    display(container)

    page_session.locator(".test-class-latex >> .mrel").wait_for()
    page_session.evaluate("document.fonts.ready")
    page_session.wait_for_timeout(1000)
    assert_solara_snapshot(page_session.locator(".test-class-latex").screenshot(), postfix=widgets_postfix)
    label.value = r"$\alpha$"
    label.add_class("test-changed-class-latex")
    page_session.locator(".test-changed-class-latex >> .mathnormal").wait_for()
    page_session.evaluate("document.fonts.ready")
    page_session.wait_for_timeout(1000)
    assert_solara_snapshot(page_session.locator(".test-changed-class-latex").screenshot(), postfix=widgets_postfix + "-changed")
