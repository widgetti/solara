# use_effect

```python
def use_effect(
    effect: EffectCallable,
    dependencies: Any | None = None
) -> None
    ...
```

Execute non-declarative code within a callback, for instance to add event handlers. `effect` is executed *after* page render, letting us fetch the actual underlying widget object using `solara.get_widget` on an element. `dependencies` should be a list of variables, which when changed trigger re-execution of `effect`. If left empty, `effect` will never re-execute. 

`effect` can return a cleanup function, which will be called before re-execution of `effect`, or when the component containing `use_effect` is removed.

Example use of `use_effect` to attach an event handler to a solara component:

```python
def use_event(el: solara.Element, callback: Callable):
    def add_event_handler():
        def on_enter(widget, event, data):
            callback(widget.v_model)

        widget = cast(ipyvue.VueWidget, solara.get_widget(el))
        widget.on_event("keyup.enter", on_enter)

        def cleanup():
            widget.on_event("keyup.enter", on_enter, remove=True)

        return cleanup

    solara.use_effect(add_event_handler, dependencies=[])

@solara.component
def Page():
    def function():
        #Do something...
    
    input = solara.InputText():
    use_event(input, function)
    ...
```

See also the [Reacton docs](https://reacton.solara.dev/en/latest/api/#use_effect).