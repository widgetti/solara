from solara.reactive import reactive

app_mounted = reactive(False)
# Outside a kernel (a notebook, plain Python) the global scope is used, and there the app shows at
# once. Each server kernel starts from the default, False.
app_mounted.value = True
app_mounted.__doc__ = """True once the browser shows the app, per kernel.

Solara keeps its "Loading app" screen until the first render of the page is done, including
the passes that state set in effects causes. Read this reactive to keep slow work out of that
render: render a skeleton while it is False, and start loading data once it is True.

```python
@solara.component
def Page():
    mounted = solara.lab.app_mounted.value
    result = solara.lab.use_task(load_data, dependencies=[mounted] if mounted else None)
    if not mounted or result.pending:
        return Skeleton()
    ...
```

The server sets it to True right after it tells the browser the first render is done (and again
after a hot reload). That set renders every component that reads it, as a separate render.
A reconnect keeps the kernel, and the value stays True.
Outside a kernel (a notebook, plain Python) it is True. In a kernel that the server did not run
(`solara.render` in a test) nothing sets it, so set it yourself there.
"""
