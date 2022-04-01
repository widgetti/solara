import inspect

from solara.components import MarkdownIt
from solara.kitchensink import react, w


@react.component
def Sample(code, component):
    locals = globals().copy()
    exec(code, locals)
    c = locals[component]
    with w.VBox() as main:
        MarkdownIt(
            f"""
```python
{code}
```
"""
        )
        c()
    return main


@react.component
def IncludeComponent(component, pre="", highlight=[], **kwargs):
    code = inspect.getsource(component.f)
    with w.VBox(layout={"padding": "20px", "max_width": "1024px", "border": "1px #333 solid"}) as main:
        MarkdownIt(
            f"""
```python
{pre}{code}
```
""",
            highlight=highlight,
        )
        component(**kwargs)
    return main
