# Toestand state management

Toestand is a no-boilerplate, state management library that integrates well with Solara. It allows your state to live outside of the Solara components, and have multiple components listen to, or update parts of the state.

Toestand wraps your state in a State object with a `.get()` and `.set(..)` and `.subscribe(callback)` which make your state "observable". This allows Solara components to listen to state changes and trigger a re-render. It is typed where possible, so you have as few runtime problems and can rely on mypy to spot issues.
A convienent `.use()` method can be used inside a Solara component to make it automatically update when changes occur (your component will be responsive).

Toestand is inspired on [Zustand](https://github.com/pmndrs/zustand).  The word "toestand" means "state" in Dutch, but can also be interpreted as "hassle".

# Simplest possible example

The State class can be used outside of Solara components, by using `.set`, `.get` and `.subscribe`:

```py
from solara.lab import State

counter_state = State(0)

# this will print out the value every time someone calls .set(..)
unsubscribe = counter_state.subscribe(print)

# this triggers all subscribers
counter_state.set(2)
# prints: 2

# The return value of .subscribe is an unsubscribe function
unsubscribe()  # remove event listener

# And we can also simply request the latest value
print(counter_state.get())
# prints: 2
```

# Integration with Solara components.

The `.use()` method calls `.get()` and will also set up subscribing (and unsubscribing) automically for you. For example:

We can now use this in a Solara application:

```python
import solara
from solara.lab import State

counter_state = State(0)


@solara.component
def CounterView():
    # .get() *and* .subscribe() to changes from a component
    count = counter_state.use()
    return solara.Info(f"Counter value {count}")


@solara.component
def CounterControl():
    def increase_counter():
        # this will trigger any component that used .use()
        # or anyone that .subscribed to changes
        counter_state.set(counter_state.get() + 1)
    return solara.Button("Increase counter", on_click=increase_counter)


@solara.component
def Page():
    with solara.VBox() as main:
        CounterView()
        CounterControl()
    return main
```

# More complex state

Application state is usually more than a primitive such as an int of a string.
A common way to store application state is to wrap it in a class using [dataclass](https://docs.python.org/3/library/dataclasses.html), [Pydantic](https://pydantic-docs.helpmanual.io/), [`attrs`](https://www.attrs.org/en/stable/) or even a `TypedDict`.

```python
import dataclasses

# Immutable/frozen is always safest
@dataclasses.dataclass(frozen=True)
class UserProfile:
    username: str = None
    logged_in: bool = False
    wrong_login: bool = False

```

## Custom State class

To keep as much of our code outside of our UI, we create a subclass of State with methods to do modifications to our state.

```python

class UserProfileState(State[UserProfile]):
    def login(self, username: str, password: str):
        # Note: in reality this should query a database
        if username == "test" and password == "test":
            self.set(UserProfile(username=username, logged_in=True, wrong_login=False))
        else:
            self.set(UserProfile(wrong_login=True))

    def logout(self):
        self.set(UserProfile())

user_profile_state = UserProfileState(UserProfile())
```


## Putting this together in an app.

We can now create the UI components that contain as little logic as possible, and only interfaces to our custom State class.

```python
@solara.component
def LoginStatus():
    user_profile = user_profile_state.use()
    with solara.VBox() as main:
        if user_profile.logged_in:
            solara.Text(f"Welcome {user_profile.username}")
        else:
            solara.Warning("Please log in")
    return main


@solara.component
def LoginForm():
    username, set_username = solara.use_state("")
    password, set_password = solara.use_state("")
    with solara.VBox() as main:
        if user_profile_state.use().wrong_login:
            solara.Warning("Wrong username or password")
        if user_profile_state.use().logged_in:
            solara.Button(label="Logout", on_click=lambda: user_profile_state.logout())
        else:
            solara.InputText(label="Username", value=username, on_value=set_username)
            solara.InputText(label="Password", password=True, value=password, on_value=set_password)
            solara.Button(label="Login", on_click=lambda: user_profile_state.login(username, password))
    return main


@solara.component
def Page():
    with solara.VBox() as main:
        LoginStatus()
        LoginForm()
    return main
```


<!-- # Advanced

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

TODO: solara try link -->
