---
title: Testing your Solara application, both front and back end
description: Using solara you can test both the front and back end functionalities of your application.
---

# Testing with Solara

When possible, we recommend to test your application without a browser. This is faster and more reliable than testing with a browser. Testing via a browser is more difficult to get right due to having to deal with two processes that communicate
asynchronously (the Python process and the browser process).

Only when you develop new components that rely on new frontend code or CSS do we recommend considering using a browser to test your component or application.

## Testing without a Browser

When testing a component or application without a browser, we recommend to use vanilla [pytest](https://docs.pytest.org/) to test the application logic.

To get inspiration for writing tests that cover component logic and their interactions with existing components, refer to the [tests in the Solara repository](https://github.com/widgetti/solara/tree/master/tests).

The following example demonstrates how to test a simple Solara component using pytest:

```python
import solara
import ipyvuetify as v


def test_docs_no_browser_simple():
    clicks = solara.reactive(0)

    @solara.component
    def ClickButton():
        def increment():
            clicks.value += 1

        solara.Button(label=f"Clicked: {clicks}", on_click=increment)

    # rc is short for render context
    box, rc = solara.render(ClickButton(), handle_error=False)
    button = box.children[0]
    assert isinstance(button, v.Btn)
    assert button.children[0] == "Clicked: 0"
    # trigger the click event handler without a browser
    button.click()
    assert clicks.value == 1
    assert button.children[0] == "Clicked: 1"
```

Here we let Solara render the component into a set of widgets without a frontend (browser) connected.
We check the resulting ipywidgets and its properties using `asserts`, as is standard with pytest.
We also show how to trigger the click handler from the Python side using [`ipyvue`'s](https://github.com/widgetti/ipyvue) `.click()` method
on the widget, again without requiring a browser.

Run this test with pytest as follows:

```bash
pytest tests/unit/test_docs_no_browser_simple.py
```


### Finding a widget in the widget tree

When widgets are embedded in a larger widget tree, it becomes cumbersome to find the widget you are looking for using `.children[0].children[1]...` etc. For this use case we can use the `rc.find` method to look for a particular widget. This API is inspired on the playwright API, and is a convenient way to find a widget in the widget tree.

```python
import solara
import ipyvuetify as v


def test_docs_no_browser_api_find():
    clicks = solara.reactive(0)

    @solara.component
    def ClickButton():
        def increment():
            clicks.value += 1

        with solara.Card("Button in a card"):
            with solara.Column().meta(ref="my_column"):
                solara.Button(label=f"Clicked: {clicks}", on_click=increment)
            with solara.Column():
                solara.Button(label="Not the button we need")

    # rc is short for render context
    box, rc = solara.render(ClickButton(), handle_error=False)
    # this find will make the .widget fail, because it matches two buttons
    # finder = rc.find(v.Btn)
    # We can refine our search by adding constraints to attributes of the widget
    button_locator = rc.find(v.Btn, children=["Clicked: 0"])
    # basics asserts are supported, like assert_single(), assert_empty(), assert_not_empty()
    button_locator.assert_single()
    button = button_locator.widget
    # .find calls can also be nested, and can use the meta_ref to find the right widget
    # finder = rc.find(meta_ref="my_column").find(v.Btn)
    button.click()
    assert clicks.value == 1
    rc.find(v.Btn, children=["Clicked: 1"]).assert_single()
```

By including keywords arguments to the `find` method, we can get more specific about the widget we are looking for.
In the above example, a simple `.find(v.Btn)` would find two buttons, while `.find(v.Btn, children=["Clicked: 0"])` will find the button we are looking for. *(Note that this does require knowing about the internal implementation
of the Button component: i.e. `solara.Button` creates a `v.Btn`, and the label argument causes the button having `children=["Clicked 0"]`)*.


Because sometimes it is difficult to find a specific widget, we made is possible to attach meta data to a widget and
use that to find widgets. Together with nesting (i.e. `.find(...).find(...)`) calls, this makes it easier to find the widget you are looking for in
larger applications. In the above example we could have replaced the `.find(v.Btn, children=["Clicked: 0"])` with
`.find(meta_ref="my_column").find(v.Btn)` to find the button we are looking for.

Especially in larger application, adding meta data to widgets makes it much easier to find the widget you are looking for, as well
as correlate the testing code back to the application code. Having unique meta_refs makes searching through your codebase and in your tests much easier.

### Asynchronous updating of the UI

When a [`solara.lab.task`](https://solara.dev/api/task) is executed, a new thread will spawn, which will likely update the UI somewhere in the future. We can wait for the UI to update using the `wait_for` method on the finder object. This method will poll the widget tree, waiting for the widget to appear. If the timeout is reached, the test will fail.

```python
import solara
import solara.lab
import ipyvuetify as v
import time


def test_docs_no_browser_api_thread():
    clicks = solara.reactive(0)

    @solara.component
    def ClickButton():
        @solara.lab.task
        def increment():
            # now we will wait for 0.3 seconds before updating the UI
            time.sleep(0.3)
            clicks.value += 1

        with solara.Card("Button in a card"):
            with solara.Column():
                solara.Button(label=f"Clicked: {clicks}", on_click=increment)

    # rc is short for render context
    box, rc = solara.render(ClickButton(), handle_error=False)
    finder = rc.find(v.Btn)
    button = finder.widget
    finder.assert_single()
    finder.assert_not_empty()
    assert button.children[0] == "Clicked: 0"

    # clicking will now start a thread, so we have to wait/poll for the UI to update
    button.click()

    button_after_delayed_click = rc.find(v.Btn, children=["Clicked: 1"])
    button_after_delayed_click.wait_for(timeout=2.5)
```

## Testing with a Browser

As mentioned in the introduction, when you develop new components that need frontend code or CSS, we recommend considering using a browser to test your component or application. Although these tests are slower to run and more
difficult to get right, they may be crucial to ensure the correct rendering of your components or application.


### Installation

We recommend using the `pytest-ipywidgets` pytest plugin together with [Playwright for Python](https://playwright.dev/python/) to test your widgets, components or applications using a browser, for both unit as well as integration tests.

Unit tests often test a single component, while integration (or smoke tests) usually tests your whole application, or a large part of it.

To install `pytest-ipywidgets` and Playwright for Python, run the following commands:
```
$ pip install "pytest-ipywidgets[solara]"  # or "pytest-ipywidgets[all]" if you also want to test with Jupyter Lab, Jupyter Notebook and Voila.
$ playwright install chromium
```

### Testing widgets using Solara server

The most convenient way to test a widget, is by including the `solara_test` fixture in your test function arguments. Here's an example:

```python
import ipywidgets as widgets
import playwright.sync_api
from IPython.display import display

def test_widget_button_solara(solara_test, page_session: playwright.sync_api.Page):
    # The test code runs in the same process as solara-server (which runs in a separate thread)
    # Note: this test uses ipywidgets directly, not solara components.
    button = widgets.Button(description="Click Me!")

    def change_description(obj):
        button.description = "Tested event"

    button.on_click(change_description)
    display(button)
    button_sel = page_session.locator("text=Click Me!")
    button_sel.wait_for()
    button_sel.click()
    page_session.locator("text=Tested event").wait_for()
```
When this fixture is used, we can use the standard IPython display call to add your widget to the page. Using the `page_session` fixture, we can interact with the widget in the browser,
in this case we trigger a button click in the browser and check if the button description changes to "Tested event".

Run this test with pytest as follows:

```bash
pytest tests/ui/test_widget_button.py --headed # remove --headed to run headless
```


### Testing state changes on the Python side with polling

In the above example, an event in the frontend led to a state change on the Python side which is reflected in
the frontend, so we could use Playwright to test if our event handler was executed correctly.

However, sometimes we want to test if a state changed on the Python side that has no
direct effect on the frontend. A possible example is is a successful database write, or an update to a
Python variable.

The following example uses a polling technique to check if a state change happened on the Python side.

```python
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
```

### Testing state changes on the Python side with a Future

Sometimes, state changes on the Python side emit an event that we can capture. In this case,
we can use a `concurrent.futures.Future` to block until the state change happens. This is a more
efficient way to wait for a state change than polling.

```python
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
```


### Testing in Voila, Jupyter Lab, Jupyter Notebook, and Solara

In case you want to test your component in the multiple Jupyter environments (e.g., Jupyter Notebook, Jupyter Lab, Voila, and Solara) to ensure it renders correctly, use the `ipywidgets_runner` fixture to run code snippets. Here's an example:

```python
import ipywidgets as widgets
import playwright.sync_api
from IPython.display import display


def test_solara_button_all(ipywidgets_runner, page_session: playwright.sync_api.Page, assert_solara_snapshot):
    # this function (or rather its lines) will be executed in the kernel
    # voila, lab, classic notebook and solara will all execute it
    def kernel_code():
        import solara

        @solara.component
        def Button():
            text, set_text = solara.use_state("Click Me!")

            def on_click():
                set_text("Tested event")

            solara.Button(text, on_click=on_click)

        display(Button())

    ipywidgets_runner(kernel_code)
    button_sel = page_session.locator("button >> text=Click Me!")
    assert_solara_snapshot(button_sel.screenshot())
    button_sel.wait_for()
    button_sel.click()
    page_session.locator("button >> text=Tested event").wait_for()
    page_session.wait_for_timeout(1000)
```

Note that the function in the code will be executed in a different process (a Jupyter kernel), which will make it harder to debug and slower to run.
Because the function code executes in the kernel, you do not have access to local variables. However, by passing a dictionary as second argument
to `ipywidgets_runner` we can pass in extra local variables (e.g. `ipywidgets_runner(kernel_code, {"extra_argument": extra_argument})`).

These tests run slow, and are generally only recommended for ipywidgets authors that want to test if their library works in all Jupyter environments. We use these kinds of tests in libraries such as [ipyvue](https://github.com/widgetti/ipyvue), [ipyvuetify](https://github.com/widgetti/ipyvuetify), [ipyaggrid](https://github.com/widgetti/ipyaggrid), but should in general not be needed for most applications.


### Limiting the Jupyter Environments
To limit the ipywidgets_runner fixture to only run in a specific environment, use the `SOLARA_TEST_RUNNERS` environment variable:

 * `SOLARA_TEST_RUNNERS=solara pytest tests/ui`
 * `SOLARA_TEST_RUNNERS=voila pytest tests/ui`
 * `SOLARA_TEST_RUNNERS=jupyter_lab pytest tests/ui`
 * `SOLARA_TEST_RUNNERS=jupyter_notebook pytest tests/ui`
 * `SOLARA_TEST_RUNNERS=solara,voila pytest tests/ui`



### Organizing Tests and Managing Snapshots
We recommend organizing your visual tests in a separate directory, such as `tests/ui`. This allows you to run fast tests (`test/unit`) separately from slow tests (`test/ui`). Use the `solara_snapshots_directory` fixture to change the default directory for storing snapshots, which is `tests/ui/snapshots` by default.

```bash
$ pytest tests/unit  # run fast test
$ pytest tests/ui    # run slow test
$ pytest tests       # run all tests
```

To compare a captured image from a part of your page with the reference image, use the `assert_solara_snapshot` fixture. For example, `assert_solara_snapshot(button_sel.screenshot())` will take a screenshot of the button and compare it to the reference image. If the images are different, the test will fail.

For local development, you can use the --solara-update-snapshots flag to update the reference images. This will overwrite the existing reference images with the new ones generated during the test run. However, you should carefully review the changes before committing them to your repository to ensure the updates are accurate and expected.


### Continuous Integration Recommendations

When a test fails, the output will be placed in a directory structure similar to what would be put in the `solara_snapshots_directory` directory but under the test-results directory in the root of your project (unless changed by passing `--output=someotherdirectory` to pytest).

In CI, we recommend downloading this directory using, for example, GitHub Actions:

```yaml
- name: Download test results
  uses: actions/download-artifact@v2
  with:
    name: myproject-test-results
    path: test-results
```


After inspecting and approving the screenshots, you can copy them to the `solara_snapshots_directory` directory and commit them to your repository. This way, you ensure that the reference images are up-to-date and accurate for future tests.


### Note about the Playwright

Visual testing with solara is based on [Playwright for Python](https://playwright.dev/python/), which provides a `page` fixture. However, this fixture will make a new page for each test, which is not what we want. Therefore, we provide a `page_session` fixture that will reuse the same page for all tests. This is important because it will make the tests faster.

By following these recommendations and guidelines, you can efficiently test your Solara applications and ensure a smooth developer experience.

### Configuration

#### Changing the Hostname

To configure the hostname the socket is bound to when starting the test server, use the `HOST` or `SOLARA_HOST` environment variable (e.g. `SOLARA_HOST=0.0.0.0`). This hostname is also used for the jupyter server and voila. Alternatively the `--solara-host` argument can be passed on the command line for pytest.

#### Changing the Port

To configure the ports the socket is bound to when starting the test servers, use the `PORT` environment variable (e.g. `PORT=18865`). This port and subsequent port will be used for solara-server, jupyter-server and voila. Alternatively the `--solara-port` argument can be passed on the command line for pytest for the solara server, and `--jupyter-port` and `--voila-port` for the ports of jupyter server and voila respectively.

#### Vuetify warmup

By default, we insert an ipyvuetify widget with an icon into the frontend to force loading all the vuetify assets, such as CSS and fonts. However, if you are using the solara test plugin to test pure ipywidgets or a 3rd ipywidget based party library you might not need this. Disable this vuetify warmup phase by passing the `--no-solara-vuetify-warmup` argument to pytest, or setting the environment variable `SOLARA_TEST_VUETIFY_WARMUP` to a falsey value (e.g. `SOLARA_TEST_VUETIFY_WARMUP=0`).

#### Changing the application wait timeout

By default, we wait for 10 seconds for the browser to connect to the server when the solara server is used for testing. On slower systems, this may be too short. To change this timeout, set the `PYTEST_IPYWIDGETS_SOLARA_APP_WAIT_TIMEOUT` environment variable to the desired value in seconds (e.g. `PYTEST_IPYWIDGETS_SOLARA_APP_WAIT_TIMEOUT=20`).
