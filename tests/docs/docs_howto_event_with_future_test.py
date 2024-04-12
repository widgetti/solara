import ipywidgets as widgets
from concurrent.futures import Future
import playwright.sync_api
from IPython.display import display


def future_trait_change(widget, attribute):
    """Returns a future that will be set when the trait changes."""
    future = Future()  # type: ignore

    def on_change(change):
        # set_result will cause the .result() call below to resume
        future.set_result(change["new"])
        widget.unobserve(on_change, attribute)

    widget.observe(on_change, attribute)
    return future


def test_event_with_polling(solara_test, page_session: playwright.sync_api.Page):
    button = widgets.Button(description="Reset slider")
    slider = widgets.IntSlider(value=42)

    def on_click(button):
        # change the slider value trait when the button is clicked
        # this will be called from the thread the websocket from solara-server
        # is running in, so we can block from the main thread (that pytest is running in)
        slider.value = 0

    button.on_click(on_click)
    display(button)
    # we could display the slider, but it's not necessary for this test
    # since we are only testing if the value changes on the Python side
    # display(slider)
    button_sel = page_session.locator("text=Reset slider")

    # create the future with the attached observer *before* clicking the button
    slider_value = future_trait_change(slider, "value")
    # trigger the click event handler via the frontend, this makes sure that
    # the event handler (on_click) gets executed in a separate thread
    # (the one that the websocket from solara-server is running in)
    button_sel.click()

    # .result() blocks until the value changes or the timeout condition is met.
    # If no value is set, the test will fail due to a TimeoutError
    assert slider_value.result(timeout=2) == 0
