"""
# Route

See also [Understanding Routing](/docs/understanding/routing). and [`use_route`](use_route)


```python
# in solara namespace
%s
```

"""

import inspect

import solara

__doc__ = __doc__ % inspect.getsource(solara.Route)


@solara.component
def Page():
    return solara.Text("")
