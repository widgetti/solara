# Quickstart

This 1-minute quickstart will get you to:

   * Solara install.
   * Write your first Solara script.
   * Run your script using Solara server.
   * (Optional) Reuse your code in the Jupyter notebook.

## You should know

This quickstart will assume:

  * You have successfully installed Solara

If not, please follow the [Installation instructions](/docs/installing).


## First script

Put the following content in a file, say `sol.py`:

```solara
import numpy as np
import plotly.express as px

import solara

x = np.linspace(0, 2, 100)


@solara.component
def Page():
    freq, set_freq = solara.use_state(2.0)
    phase, set_phase = solara.use_state(0.1)
    y = np.sin(x * freq + phase)

    with solara.VBox() as main:
        solara.FloatSlider("Frequency", value=freq, on_value=set_freq, min=0, max=10)
        solara.FloatSlider("Phase", value=phase, on_value=set_phase, min=0, max=np.pi, step=0.1)

        fig = px.line(x=x, y=y)
        solara.FigurePlotly(fig)
    return main
```

Yes, the above example is running live on the Solara documentation web server. If you change the slider the graph updates.

## Run the script using Solara server

Run from the command line in the same directory where you put your file (`sol.py`):

```bash
$ solara run sol.py
Solara server is starting at http://localhost:8765
```

If you open the URL in your browser ([http://localhost:8765](http://localhost:8765)), you should see the same graph in your browser, now running on your computer.

## Reuse your code in the Jupyter notebook.

From Jupyter Notebook (classic) or Jupyter Lab, navigate to the same directory as `sol.py`. Enter the following code in a notebook cell:

```python
from sol import Page()
display(Page)
```

You should see the following output:

<img src="/static/public/quickstart-notebook.png" alt="Markdown Monster icon" style="border: 1px solid #ccc;" />
