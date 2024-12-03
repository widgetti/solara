import inspect

import solara
from solara.alias import rw
from solara.components import Markdown


@solara.component
def Sample(code, component):
    locals = globals().copy()
    exec(code, locals)
    c = locals[component]
    with rw.VBox() as main:
        Markdown(
            f"""
```python
{code}
```
"""
        )
        c()
    return main


@solara.component
def IncludeComponent(component, pre="", highlight=[], **kwargs):
    code = inspect.getsource(component.f)
    with rw.VBox(layout={"padding": "20px", "max_width": "1024px", "border": "1px #333 solid"}) as main:
        Markdown(
            f"""
```python
{pre}{code}
```
""",
            highlight=highlight,
        )
        component(**kwargs)
    return main
