"""
# use_previous

```python
def use_previous(value: T) -> T:
    ...
```

Returns the value from a previous render phase, or the current value on the first render.


"""
from solara.alias import reacton, sol


@reacton.component
def Page():
    value, set_value = reacton.use_state(4)
    value_previous = sol.use_previous(value)
    with sol.VBox() as main:
        sol.IntSlider("value", value=value, on_value=set_value)
        sol.Markdown(
            f"""
        **Current**:  `{value}`

        **Previous**: `{value_previous}`
"""
        )

    return main
