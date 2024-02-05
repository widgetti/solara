"""
# on_kernel_start API

Solara provides a way to run code when the virtual python kernel (re)starts.

```python
def on_kernel_start(f: Callable[[], Optional[Callable[[], None]]]):
```

`f` will be called on virtual kernel (re)start. This means that the callbacks are executed separately for all clients.
The (optional) function returned by `f` will be called on kernel close.

Note that the functions are called in inverse order with respect to the order they were registered in.
"""

from . import NoPage

title = "on_kernel_start"
Page = NoPage
