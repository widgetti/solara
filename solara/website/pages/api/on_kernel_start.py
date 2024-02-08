"""
# on_kernel_start

Run a function when a virtual kernel (re)starts and optionally run a cleanup function on shutdown.

```python
def on_kernel_start(f: Callable[[], Optional[Callable[[], None]]]):
```

`f` will be called on each virtual kernel (re)start. This (usually) happens each time a browser tab connects to the server
[see solara server for more details](https://solara.dev/docs/understanding/solara-server).
The (optional) function returned by `f` will be called on kernel shutdown.

Note that the cleanup functions are called in reverse order with respect to the order in which they were registered
(e.g. the cleanup function of the last call to `on_kernel_start` will be called first on kernel shutdown)
"""

from . import NoPage

title = "on_kernel_start"
Page = NoPage
