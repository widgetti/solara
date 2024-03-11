from typing import Callable, Optional, TypeVar, Union

import solara

T = TypeVar("T")


def use_reactive(
    value: Union[T, solara.Reactive[T]],
    on_change: Optional[Callable[[T], None]] = None,
) -> solara.Reactive[T]:
    """Creates a reactive variable with the a local component scope.

    It is a useful alternative to `use_state` when you want to use a
    reactive variable for the component state.
    See also [our documentation on state management](/docs/fundamentals/state-management).

    If the variable passed is a reactive variable, it will be returned instead and no
    new reactive variable will be created. This is useful for implementing component
    that accept either a reactive variable or a normal value along with an optional `on_change`
    callback.

    Note that that on each call, if the value changes, the reactive variable will be updated.
    For objects that do no implement equality comparison, the will lead to an infinite loop.

    In that case, combine the `use_reactive` with `use_memo` to never trigger an update from
    the render function.

    ```python
    @solara.component
    def Page():
        data = solara.use_reactive(solara.use_memo(lambda: MyDataObject()))
        ...
    ```

    ## Arguments:

     * value (Union[T, solara.Reactive[T]]): The value of the
            reactive variable. If a reactive variable is provided, it will be
            used directly. Otherwise, a new reactive variable will be created
            with the provided initial value. If the argument passed changes
            the reactive variable will be updated.

     * on_change (Optional[Callable[[T], None]]): An optional callback function
            that will be called when the reactive variable's value changes.

    Returns:
        solara.Reactive[T]: A reactive variable with the specified initial value
            or the provided reactive variable.

    ## Examples

    ### Replacement for use_state
    ```solara
    import solara

    @solara.component
    def ReusableComponent():
        color = solara.use_reactive("red")  # another possibility
        solara.Select(label="Color",values=["red", "green", "blue", "orange"],
                    value=color)
        solara.Markdown("### Solara is awesome", style={"color": color.value})

    @solara.component
    def Page():
        # this component is used twice, but each instance has its own state
        ReusableComponent()
        ReusableComponent()

    ```

    ### Flexible arguments

    The `MyComponent` component can be passed a reactive variable or a normal
    Python variable and a `on_value` callback.

    ```python
    import solara
    from typing import Union, Optional, Callable

    @solara.component
    def MyComponent(value: Union[T, solara.Reactive[T]],
                    on_value: Optional[Callable[[T], None]] = None,
        ):
        reactive_value = solara.use_reactive(value, on_value)
        # Use the `reactive_value` in the component
    ```
    """

    try:
        on_change_ref = solara.use_ref(on_change)
    except RuntimeError as e:
        raise RuntimeError(
            "use_reactive must be called from a component function, inside the render function.\n"
            "Do not call it top level, use [solara.reactive()](https://solara.dev/api/reactive) instead."
        ) from e
    on_change_ref.current = on_change

    def create():
        if not isinstance(value, solara.Reactive):
            return solara.reactive(value)

    reactive_value = solara.use_memo(create, dependencies=[])
    if isinstance(value, solara.Reactive):
        reactive_value = value
    assert reactive_value is not None
    updating = solara.use_ref(False)

    def forward_on_change():
        def forward(value):
            if on_change_ref.current and not updating.current:
                on_change_ref.current(value)

        return reactive_value.subscribe(forward)

    def update():
        updating.current = True
        try:
            if not isinstance(value, solara.Reactive):
                reactive_value.value = value
        finally:
            updating.current = False

    solara.use_memo(update, [value])
    # if value is a reactive variable, and it changes, we need to subscribe to the latest
    # reactive variable, otherwise we only link to it once
    solara.use_effect(forward_on_change, [value] if isinstance(value, solara.Reactive) else [])

    return reactive_value
