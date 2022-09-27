# Quickstart

This 1-minute quickstart will get you to:

   * Solara install.
   * Write your first Solara script.
   * Run your script using Solara server.
   * (Optional) Reuse your code in the Jupyter notebook.

## You should know

This quickstart will assume:

  * You have succesfully installed Solara

If not, please follow the [Installation instructions](/docs/installing).


## First script

Put the following content in a file, say `sol.py`:

```python
import numpy as np
import plotly.express as px

from solara.alias import reacton, sol

x = np.linspace(0, 2, 100)


@reacton.component
def Page():
    freq, set_freq = reacton.use_state(2.0)
    phase, set_phase = reacton.use_state(0.1)
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
