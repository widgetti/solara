# Making IPywidgets based web applications simple and fun

## What is it?

   * A set of components for React-IPywidgets
   * An application server to make development easier, and scaling better
   * An alternative for Voila, for when you only need to display widgets, and the kernel overhead is too much.

## Example


Create a file `myapp.py`:
```python
import react_ipywidgets as react
import react_ipywidgets.ipywidgets as w

@react.component
def ButtonClick(label="Hi"):
    clicks, set_clicks = react.use_state(0)
    return w.Button(description=f"{label}: Clicked {clicks} times",
                    on_click=lambda: set_clicks(clicks+1))
app = ButtonClick('My first app')
```

Install and run

    $ pip install solara
    $ solara myapp.py
    INFO:     Uvicorn running on http://127.0.0.1:8765 (Press CTRL+C to quit)
    INFO:     Started reloader process [50178] using watchgod
    INFO:     Started server process [50183    

The browser should open http://127.0.0.1:8765


# Installation
## User

Most users:

    $ pip install solara[server,examples]

Conda users (not yet):

    $ conda install -c conda-forge install react-ipywidgets


## Development

We use flit (`pip install flit` if you don't already have it)

    $ flit install --symlink --deps develop --extras server,examples
