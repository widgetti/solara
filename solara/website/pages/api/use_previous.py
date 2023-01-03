"""
# use_previous

```python
def use_previous(value: T) -> T:
    ...
```

Returns the value from a previous render phase, or the current value on the first render.


"""
import solara

title = "use_previous"


@solara.component
def Page():
    value, set_value = solara.use_state(4)
    value_previous = solara.use_previous(value)
    with solara.VBox() as main:
        solara.IntSlider("value", value=value, on_value=set_value)
        solara.Markdown(
            f"""
        **Current**:  `{value}`

        **Previous**: `{value_previous}`
"""
        )

    return main
