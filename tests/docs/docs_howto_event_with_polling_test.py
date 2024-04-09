import ipywidgets as widgets
import playwright.sync_api
from IPython.display import display
from typing import Callable
import time


def assert_equals_poll(getter: Callable, expected, timeout=2, iteration_delay=0.01):
    start = time.time()
    while time.time() - start < timeout:
        if getter() == expected:
            return
        time.sleep(iteration_delay)
    assert getter() == expected
    return False


def test_event_with_polling(solara_test, page_session: playwright.sync_api.Page):
    button = widgets.Button(description="Append data")
    # some data that will change due to a button click
    click_data = []

    def on_click(button):
        # change the data when the button is clicked
        # this will be called from the thread the websocket is in
        # so we can block/poll from the main thread (that pytest is running in)
        click_data.append(42)

    button.on_click(on_click)
    display(button)
    button_sel = page_session.locator("text=Append data")
    button_sel.click()

    # we block/poll until the condition is met.
    assert_equals_poll(lambda: click_data, [42])
