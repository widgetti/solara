# Testing with Solara
# Testing Application Logic

We recommend using pytest to test the application logic of your Solara components. To get inspiration for writing tests that cover component logic and their interactions with existing components, refer to the [tests in the Solara repository](https://github.com/widgetti/solara/tree/master/tests).

# Testing with a Browser

If you have custom components that depend on a connected browser because it is using JavaScript, we recommend using the Solara pytest plugin, which is installed by default when you install Solara. The plugin provides a fixture called `solara_test` that you can use to test your components. Here's an example:

```python
import ipywidgets as widgets
import playwright.sync_api
from IPython.display import display

def test_widget_button_solara(solara_test, page_session: playwright.sync_api.Page):
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
```

Run this test with pytest:

```bash
pytest tests/ui/test_widget_button.py --headed # remove --headed to run headless
```

This require playwright to be installed:

```
$ pip install playwright pytest-playwright
# $ pip install "solara[pytest]"  # if you haven't installed solara already
$ playwright install chromium
```


In this example, use the standard IPython display call to add your widget to the page.

# Testing in the main Jupyter Environments

In case you want to test your component in the main Jupyter environments (e.g., Jupyter Notebook, Jupyter Lab, Voila, and Solara) to ensure it renders correctly, use the `ipywidgets_runner` fixture to run code snippets. Here's an example:

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

## Limiting the Jupyter Environments
To limit the ipywidgets_runner fixture to only run in a specific environment, use the `SOLARA_TEST_RUNNERS` environment variable:

 * `SOLARA_TEST_RUNNERS=solara pytest tests/ui`
 * `SOLARA_TEST_RUNNERS=voila pytest tests/ui`
 * `SOLARA_TEST_RUNNERS=jupyter_lab pytest tests/ui`
 * `SOLARA_TEST_RUNNERS=jupyter_notebook pytest tests/ui`
 * `SOLARA_TEST_RUNNERS=solara,voila pytest tests/ui`



# Organizing Tests and Managing Snapshots
We recommend organizing your visual tests in a separate directory, such as `tests/ui`. This allows you to run fast tests (`test/unit`) separately from slow tests (t`est/ui`). Use the `solara_snapshots_directory` fixture to change the default directory for storing snapshots, which is `tests/ui/snapshots` by default.

```bash
$ pytest tests/unit  # run fast test
$ pytest tests/ui    # run slow test
$ pytest tests       # run all tests
```

To compare a captured image from a part of your page with the reference image, use the `assert_solara_snapshot` fixture. For example, `assert_solara_snapshot(button_sel.screenshot())` will take a screenshot of the button and compare it to the reference image. If the images are different, the test will fail.

For local development, you can use the --solara-update-snapshots flag to update the reference images. This will overwrite the existing reference images with the new ones generated during the test run. However, you should carefully review the changes before committing them to your repository to ensure the updates are accurate and expected.


# Continuous Integration Recommendations

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


# Note about the Playwright

Visual testing with solara is based on [Playwright for Python](https://playwright.dev/python/), which provides a `page` fixture. However, this fixture will make a new page for each test, which is not what we want. Therefore, we provide a `page_session` fixture that will reuse the same page for all tests. This is important because it will make the tests faster.

By following these recommendations and guidelines, you can efficiently test your Solara applications and ensure a smooth developer experience.

# Configuration

## Changing the Hostname

To configure the hostname the socket is bound to when starting the test server, use the `HOST` or `SOLARA_HOST` environment variable (e.g. `SOLARA_HOST=0.0.0.0`). This hostname is also used for the jupyter server and voila. Alternatively the `--solara-host` argument can be passed on the command line for pytest.

## Changing the Port

To configure the ports the socket is bound to when starting the test servers, use the `PORT` environment variable (e.g. `PORT=18865`). This port and subsequent port will be used for solara-server, jupyter-server and voila. Alternatively the `--solara-port` argument can be passed on the command line for pytest for the solara server, and `--jupyter-port` and `--voila-port` for the ports of jupyter server and voila respectively.

## Vuetify warmup

By default, we insert an ipyvuetify widget with an icon into the frontend to force loading all the vuetify assets, such as CSS and fonts. However, if you are using the solara test plugin to test pure ipywidgets or a 3rd ipywidget based party library you might not need this. Disable this vuetify warmup phase by passing the `--no-solara-vuetify-warmup` argument to pytest, or setting the environment variable `SOLARA_TEST_VUETIFY_WARMUP` to a falsey value (e.g. `SOLARA_TEST_VUETIFY_WARMUP=0`).
