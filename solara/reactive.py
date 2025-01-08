from typing import Any, Callable, TypeVar
import warnings

import reacton.core

from solara.toestand import Reactive
import solara.util

__all__ = ["reactive", "Reactive"]

T = TypeVar("T")


def reactive(value: T, equals: Callable[[Any, Any], bool] = solara.util.equals_extra, allow_in_render=False) -> Reactive[T]:
    """Creates a new Reactive object with the given initial value.

    Reactive objects are mostly used to manage global or application-wide state in
    Solara web applications. They provide an easy-to-use mechanism for keeping
    track of the changing state of data and for propagating those changes to
    the appropriate UI components. For managing local or component-specific
    state, consider using the [`solara.use_state()`](/documentation/api/hooks/use_state) function.


    Reactive variables can be accessed using the `.value` attribute. To modify
    the value, you can either set the `.value` property directly or use the
    `.set()` method. While both approaches are equivalent, the `.set()` method
    is particularly useful when you need to pass it as a callback function to
    other components, such as a slider's `on_value` callback.

    When a component uses a reactive variable, it
    automatically listens for changes to the variable's value. If the value
    changes, the component will automatically re-render to reflect the updated
    state, without the need to explicitly subscribe to the variable.

    Reactive objects in Solara are also context-aware, meaning that they can
    maintain separate values for each browser tab or user session. This enables
    each user to have their own independent state, allowing them to interact
    with the web application without affecting the state of other users.

    Args:
        value (T): The initial value of the reactive variable.
        equals: A function that returns True if two values are considered equal, and False otherwise.
            The default function is `solara.util.equals`, which performs a deep comparison of the two values
            and is more forgiving than the default `==` operator.
            You can provide a custom function if you need to define a different notion of equality.
        allow_in_render (bool): If True, do not warn if this function is called inside a render function.


    Returns:
        Reactive[T]: A new Reactive object with the specified initial value.

    Example:

    ```python
    >>> counter = solara.reactive(0)
    >>> counter.value
    0
    >>> counter.set(1)
    >>> counter.value
    1
    >>> counter.value += 1
    >>> counter.value
    2
    ```


    ## Solara example

    Here's an example that demonstrates the use of reactive variables in Solara components:

    ```solara
    import solara

    counter = solara.reactive(0)

    def increment():
        counter.value += 1


    @solara.component
    def CounterDisplay():
        solara.Info(f"Counter: {counter.value}")


    @solara.component
    def IncrementButton():

        solara.Button("Increment", on_click=increment)


    @solara.component
    def Page():
        IncrementButton()
        CounterDisplay()
    ```

    In this example, we create a reactive variable counter with an initial value of 0.
    We define two components: `CounterDisplay` and `IncrementButton`. `CounterDisplay` renders the current value of counter,
    while `IncrementButton` increments the value of counter when clicked.
    Whenever the counter value changes, `CounterDisplay` automatically updates to display the new value.

    """
    if not allow_in_render:
        rc = reacton.core.get_render_context(False)
        if rc:
            warnings.warn(
                "You are calling `solara.reactive()` inside a render function. This will cause the reactive variable to be re-created on every render, and reset to the initial default value. "
                "Use `solara.use_reactive()` instead, or pass `allow_in_render=True` to `solara.reactive()`.",
                stacklevel=2,
            )
    return Reactive(value, equals=equals)
