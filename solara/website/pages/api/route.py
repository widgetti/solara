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
from solara.alias import react, sol

__doc__ = __doc__ % inspect.getsource(solara.Route)


@react.component
def Page():
    return sol.Text("")
