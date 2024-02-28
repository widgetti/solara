import ipywidgets as widgets
import playwright.sync_api
import pytest
from IPython.display import display

import solara.util

from .conftest import SERVERS


def test_widget_button_solara(solara_test, page_session: playwright.sync_api.Page, assert_solara_snapshot):
    # this all runs in process, which only works with solara
    # also, this test is only with pure ipywidgets
    button = widgets.Button(description="Click Me!")

    def change_description(obj):
        button.description = "Tested event"

    button.on_click(change_description)
    display(button)
    button_sel = page_session.locator("text=Click Me!")
    button_sel.wait_for()
    button_sel.click()
    page_session.locator("text=Tested event").wait_for()
    # with ipyvuetify 2 we modified the button font for ipywidgets, that does not happen anymore with ipyvuetify 3
    # therefore we have a different screenshot for ipyvuetify 2 and 3
    assert_solara_snapshot(page_session.locator("text=Tested event").screenshot(), postfix="-ipyvuetify3" if solara.util.ipyvuetify_major_version == 3 else "")


def test_solara_button_all(ipywidgets_runner, page_session: playwright.sync_api.Page, request, assert_solara_snapshot):
    if request.node.callspec.params["ipywidgets_runner"] != "solara" and request.node.callspec.params["solara_server"] != SERVERS[0]:
        pytest.skip("No need to run this test for all servers.")

    # this function (or rather its lines) will be executed in the kernel
    # voila, lab, classic notebook and solara will all execute it
    def kernel_code():
        import solara

        @solara.component
        def Button():
            text, set_text = solara.use_state("Click Me!")

            def on_click():
                set_text("Tested event")

            with solara.Row():
                solara.Button(text, on_click=on_click)

        display(Button())

    ipywidgets_runner(kernel_code)
    button_sel = page_session.locator("button >> text=Click Me!")
    assert_solara_snapshot(button_sel.screenshot())
    button_sel.wait_for()
    button_sel.click()
    page_session.locator("button >> text=Tested event").wait_for()
    page_session.wait_for_timeout(1000)


def test_slider_all(ipywidgets_runner, page_session: playwright.sync_api.Page, request, assert_solara_snapshot):
    if request.node.callspec.params["ipywidgets_runner"] != "solara" and request.node.callspec.params["solara_server"] != SERVERS[0]:
        pytest.skip("No need to run this test for all servers.")

    # this function (or rather its lines) will be executed in the kernel
    # voila, lab, classic notebook and solara will all execute it
    def kernel_code():
        import ipywidgets as widgets

        slider = widgets.FloatSlider(value=7.5, min=5.0, max=10.0, step=0.1, description="FloatSlider")
        box = widgets.HBox([slider])
        box.add_class("my-slider")
        # we do not want it full with, which depends on environment/browser window size
        box.layout.width = "400px"
        display(box)

    ipywidgets_runner(kernel_code)
    slider_sel = page_session.locator(".my-slider")
    assert_solara_snapshot(slider_sel.screenshot(), postfix="-ipywidgets-" + str(solara.util.ipywidgets_major))
    page_session.wait_for_timeout(1000)
