# Toestand state management

Toestand is a no-boilerplate, state management library that integrates well with Solara and avoids shooting yourself in the foot accidently. Toestand wraps you state object in a Store object with a `.get()` and `.update(..)` which turns it into an observable object such that Solara/React-IPywidgets can listen to state changes and trigger a re-render. It is typed where possible, so you have as little runtime problems, and can rely on mypy to spot issues.

Toestand is inspired on [Zustand](https://github.com/pmndrs/zustand).  The word "toestand" means "state" in Dutch, but can also be interpreted as "hassle".

We separate:

   * `State` - The data interface, in memory storage. Optional if you don't care about type safetly.
   * `Store` - Manages access to the data (`.get` and `.update`) and adds observability (`.subscribe`/`.unsubscribe`).
   * `Storage` - Where the data is stored (Memory, Disk, Redis?), and its scope (1 per user, connection, worker, application, ... ?).

# Simplest possible example

This example does not use any type safety, it just stored data in a dictionary.

```py
from solara.toestand import Store

settings = Store({"bears": 2, "theme": "dark"})
unsub = settings.subscribe(print)

settings.update(theme="light")
# prints: {"bears": 2, "theme": "light"}

unsub()  # remove event listener

```

We can now use this in a React application:
```py
import react_ipywidgets as react
import solara as sol


@react.component
def ThemeInfo():
    # the lambda function here is called a selector, it 'selects' out the state you want
    theme = settings.use(lambda state: state["theme"])
    return sol.Info(f"Using theme {theme}")


@react.component
def ThemeSelector():
    theme, set_theme = settings.use_field(settings.fields["theme"])
    with sol.ToggleButtonsSingle(theme, on_value=set_theme) as main:
        sol.Button("dark")
        sol.Button("light")
    return main


@react.component
def Page():
    with sol.VBox() as main:
        ThemeInfo()
        ThemeSelector()
    return main
```

# State class

A user defined class with (typed) fields describing what you need to store.

```python

# Immutable/frozen is always safest
@dataclasses.dataclass(frozen=True)
class BearState:
    type: str
    count: int

```

You can use Python `dataclasses`, [Pydantic](https://pydantic-docs.helpmanual.io/) or [`attrs`](https://www.attrs.org/en/stable/), or even a `TypedDict`. Whatever your feel comfortable with.


# Store class

This is where you put your methods in that do some logic, some call it business logic. But they can also be meaningful methodnames that do simple state mutations, such as here.

```python
from solara.toestand import Store, SubStorageAttr, use_sync_external_store


# we use a Generic (Store[BearState]) to make .get() return the right type
# to make our editor autocomplete and give us type checks via mypy
class BearStore(Store[BearState]):
    def increase_population(self):
        # .get always returns the latest `BearState` object
        self.update(count=self.get().count + 1)
        # Note that update does not check types due to typing limitations in Python
```

We never mutate the state directly, but can only update it using `.update(...)`. Note that not all keys need to be given,  update will only update the keys it it being passed (`count` in this case).

Since we use the `.update(...)` method, any listeners that subscribed to changes via `.subscribe(...)` will be notified.



# Usage in React

```python
import react_ipywidgets as react
import solara as sol
import solara.scope


bear_state_initial = BearState(type="brown", count=2)
bear_store = BearStore(bear_state_initial)

@react.component
def BearCounter():
    # the lambda function here is called a selector, it 'selects' out the state you want
    bear_count = bear_store.use(lambda bear: bear.count)
    return sol.Info(f"{bear_count} bears around here")

```

By using the `store.use(some_selector)` toestand will only give us the data we need, and will only re-render our component when the data we need changes (in this case `.count`). Our component will thus no re-render when the `.type` changes value.

Toestand finds out if it needs to update the react component by calling the selector function after any state change and comparing that to the previous result. This avoids unneeded updates to your component.



## Changing state

Changing the state can be done calling a method on the store:

```py
@react.component
def Controls1():
    return sol.Button("add bear", on_click=bear_store.increase_population)
```

Using the special `setter/fields` combination:
```py
@react.component
def Controls2a():
    return sol.IntSlider("set bear", on_value=bear_store.setter(bear_store.fields.count))
```
*Note that the "setter + fields" method may look a bit odd, but the only way we generate a type safe setter due to type limitations in Python*


Or simply using a lambda+update:
```py
@react.component
def Controls2a():
    return sol.FloatSlider("set bear", on_value=lambda value: bear_store.update(count=value))

```

# Storage

In the previous example `bear_store` is a global variable, however, when running in the Solara server, each `connection` (e.g. each browser tab) will have it's own state, nothing is shared by default. This means each user/browser tab will have its own `BearState.count` value.
Outside of the Solara server (e.g. in a Jupyter environment), there is only a single state, since there are no multiple users.

If you do want to have a single shared state (currently only a worker/process scope is supported), use a different storage scope.

```py
import solara.scope

bear_store = BearStore(bear_state, storage=solara.scope.worker)
```

# Complete working example

This example can be copy pasted and should work using `$ solara run app.py`

```py
import dataclasses

import react_ipywidgets as react

import solara as sol
from solara.toestand import Store


@dataclasses.dataclass(frozen=True)
class BearState:
    type: str
    count: int


class BearStore(Store[BearState]):
    def increase_population(self):
        self.update(count=self.get().count + 1)


bear_state_initial = BearState(type="brown", count=2)
bear_store = BearStore(bear_state_initial)


@react.component
def BearCounter():
    bear_count = bear_store.use(lambda bear: bear.count)
    return sol.Info(f"{bear_count} bears around here")


@react.component
def Controls():
    return sol.Button("add bear", on_click=bear_store.increase_population)


@react.component
def App():
    with sol.VBox() as main:
        BearCounter()
        Controls()
    return main


app = App()
```

<!-- TODO: solara try link -->
