# Quickstart

This 1-minute quickstart will get you to:

   * Solara install.
   * Write your first Solara script.
   * Run your script using Solara server.
   * (Optional) Reuse your code in the Jupyter notebook.

## Installation


### Create a virtual environment (optional)

It is best to install Solara into a virtual environment unless you know what you are doing (you already have a virtual environment, or you are using conda or docker).

See also [The Python Packaging User Guide](https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/#creating-a-virtual-environment) for more information.

Otherwise, you can go directly to the [Pip install Solara section](#pip-install-solara).


#### OSX/Unix/Linux

Setting up a virtual environment on OSX/Unix/Linux:

    $ python -m venv solara-env
    $ source ./solara-env/bin/activate

#### Windows

Setting up a virtual environment on Windows:

    > py -m venv solara-env
    > solara-env\Scripts\activate


### Pip install Solara

Now install Solara using pip:

    $ pip install solara[server,examples] watchdog


## First script

Put the following content in a file, say `sol.py`:

```python
import numpy as np
import plotly.express as px

from solara.kitchensink import react, sol

x = np.linspace(0, 2, 100)


@react.component
def Page():
    freq, set_freq = react.use_state(2.0)
    phase, set_phase = react.use_state(0.1)
    y = np.sin(x * freq + phase)

    with sol.VBox() as main:
        sol.FloatSlider("Frequency", value=freq, on_value=set_freq, min=0, max=10)
        sol.FloatSlider("Phase", value=phase, on_value=set_phase, min=0, max=np.pi, step=0.1)

        fig = px.line(x=x, y=y)
        sol.FigurePlotly(fig)
    return main
```

## Run the script using Solara server

Run from the command line in the same directory where you put your file (`sol.py`):

```bash
solara run sol.py
Solara server is starting at http://localhost:8765
```

If you open the URL in your browser ([or click here](http://localhost:8765)), you should see the following in your browser.

<img src="/static/public/quickstart-server.png" alt="Markdown Monster icon" style="border: 1px solid #ccc;" />

## (Optional) Reuse your code in the Jupyter notebook.

From Jupyter Notebook (classic) or Jupyter Lab, navigate to the same directory as `sol.py`. Enter the following code in a notebook cell:

```python
from sol import Page()
display(Page)
```

You should see the following output:

<img src="/static/public/quickstart-notebook.png" alt="Markdown Monster icon" style="border: 1px solid #ccc;" />
