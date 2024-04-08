Test ipywidgets with playwright and pytest.


# Installation

```bash
pip install "pytest-ipywidgets[all]"
```

*(Note that the optional `[all]` installs all dependencies, including compatible versions of notebook, jupyterlab and voila.)*

# Usage

## Using solara-server (in-process)

If you want to test your ipywidgets with playwright in-process, you can use the `solara_test` fixture, use `display` to
show your widget in the browser.

```python
import ipywidgets as widgets
import playwright.sync_api
from IPython.display import display

def test_widget_button_solara(solara_test, page_session: playwright.sync_api.Page):
    # this all runs in-process
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

# Testing in the main Jupyter Environments (Notebook, Lab, Voila & Solara)

See https://solara.dev/documentation/advanced/howto/testing for more information.
