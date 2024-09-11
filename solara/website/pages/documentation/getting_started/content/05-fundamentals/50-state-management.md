---
title: Introduction to state management in Solara
description: State management is a crucial aspect of building data-focused web applications with Solara. By effectively managing state, you can create interactive
    and responsive applications that react to changes in data and user input.
---
# Introduction

State management is a crucial aspect of building data-focused web applications with Solara. By effectively managing state, you can create interactive and responsive applications that react to changes in data and user input. In Solara, there are two primary ways to define state: global application state using [`solara.reactive`](/documentation/api/utilities/reactive) and local component state using [`solara.use_state`](/documentation/api/hooks/use_state) or [`solara.use_reactive`](/documentation/api/hooks/use_reactive). This article will discuss these two approaches and provide examples of how to use them in your Solara applications.

## Two main ways of defining state in Solara

### Global application state using solara.reactive

Using [`solara.reactive`](/documentation/api/utilities/reactive) allows you to create global state variables that can be accessed and modified from any component within your application. This approach is useful when you need to manage state that is shared across multiple components or when you want to maintain consistency throughout your application.

Example:

```solara
import solara

color = solara.reactive("red")

@solara.component
def SomeAppSpecificComponent():
    solara.Select(label="Color", values=["red", "green", "blue", "orange"], value=color)
    solara.Markdown("### Solara is awesome", style={"color": color.value})

@solara.component
def Page():
    SomeAppSpecificComponent()

```

In this case, the `SomeAppSpecificComponent` is not reusable in the sense that a second component has a different state. The `color` variable is global and shared across all components. This component is meant to be used only once, and mainly helps to organize the code.

You may have heard that globals are considered a bad practice. As with many things, it depends on the context. A possible downside of using a global is that it does not
allow you to create multiple instances of the same component with different states. But if the state reflects application state, there is by definition only one instance
of it needed.

### Local component state using solara.use_reactive

If you do need state that is specific to a component, you should use [`solara.use_reactive`](/documentation/api/hooks/use_reactive) hook. This hook allow you to create local state variables that are scoped to a specific component. This approach is useful when you want to encapsulate state within a component, making it self-contained and modular. Local state management is suitable for situations where state changes only affect the component and do not need to be shared across the application.


```solara hl_lines="6 8"
import solara


@solara.component
def ReusableComponent():
    color = solara.use_reactive("red")  # local state (instead of top level solara.reactive)
    solara.Select(label="Color",values=["red", "green", "blue", "orange"],
                  value=color)
    solara.Markdown("### Solara is awesome", style={"color": color.value})


@solara.component
def Page():
    # this component is used twice, but each instance has its own state
    ReusableComponent()
    ReusableComponent()

```

### Local component state using solara.use_state (not recommended)

[`solara.use_state`](/documentation/api/hooks/use_state) is a hook that might be a bit more familiar to React developers. It also allows you to create local state variables that are scoped to a specific component, however, instead of using reactive variables, it uses a tuple of a value and a setter function.

We generally recommend using `use_reactive` over `use_state` as it is more easy to refactor between global application state and local component state by switching between `use_reactive` and `reactive`. There is no equivalent for `use_state` at the global level.

If we take the previous example and replace `use_reactive` by `use_state`, we get:

Example:
```solara hl_lines="6 9"
import solara


@solara.component
def ReusableComponent():
    # color = solara.use_reactive("red")  # instead of use_reactive (not recommended)
    color, set_color = solara.use_state("red")  # local state
    solara.Select(label="Color",values=["red", "green", "blue", "orange"],
                    value=color, on_value=set_color)
    solara.Markdown("### Solara is awesome", style={"color": color})


@solara.component
def Page():
    # this component is used twice, but each instance has its own state
    ReusableComponent()
    ReusableComponent()

```

## Mutation pittfalls

In Python, strings, numbers, and tuples are immutable. This means that you cannot change the value of a string, number, or tuple in place.
Instead, you need to create a new object and assign that to a variable.

```python
a = 1
b = a
# a.value = 2  # ERROR: numbers are immutable
a = 2  # instead, re-assign a new value, the number 1 will not change
assert b == 1 # b is still 1
```
However, many objects in Python are mutable, including lists and dictionaries or potentially user defined classes. This means that you can change the value of a list, dictionary, or user defined class in place without creating a new object.
```python
a = [1, 2, 3]
b = a  # b points to the same list as a
a.append(4)  # a is now [1, 2, 3, 4]
assert b == [1, 2, 3, 4]  # b is also [1, 2, 3, 4]
```

### Not mutating lists

However, mutations in Python are not observable. **This means that if you change the value of a list, dictionary, or user defined class, Solara does not know that the value has changed and does not know it needs to re-render a component that uses that value.**

```python
import solara

reactive_list = solara.reactive([1, 2, 3])
# The next line will not trigger a re-render of a component
reactive_list.value.append(4)  # ERROR: mutating a list is not observable in Python
```

Although Solara could potentially track mutations of lists and dictionaries, that would be difficult to do for user defined classes, since we would need to know which methods mutate the object and which do not. Therefore, we have chosen not to include
any magic tracking of mutations in Solara, and instead require you to re-assign a new value to a reactive variable if you want to trigger a re-render.

```python hl_lines="5"
import solara

reactive_list = solara.reactive([1, 2, 3])
# Instead, re-assign a new value
reactive_list.value = [*reactive_list.value, 4]  # GOOD: re-assign a new list
```

### Not mutating dictionaries

A similar pattern applies to dictionaries.

```python
import solara

reactive_dict = solara.reactive({"a": 1, "b": 2})
reactive_dict.value = {**reactive_dict.value, "c": 3}  # GOOD: re-assign a new dictionary
# deleting a key
reactive_dict.value = {k: v for k, v in reactive_dict.value.items() if k != "a"}  # GOOD: re-assign a new dictionary
# deleting a key (method 2)
dict_copy = reactive_dict.value.copy()
del dict_copy["b"]
reactive_dict.value = dict_copy  # GOOD: re-assign a new dictionary
```

### Not mutating user defined classes

Or user defined classes, like a Pandas DataFrame.

```python
import solara
import pandas as pd

reactive_df = solara.reactive(pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]}))
# reactive_df.value.append({"a": 4, "b": 7})  # BAD: mutating a DataFrame is not observable in Python
df_copy = reactive_df.value.copy(deep=True)  # for Pandas 3, deep=True is not necessary
df_copy = df_copy.append({"a": 4, "b": 7}, ignore_index=True)
reactive_df.value = df_copy  # GOOD: re-assign a new DataFrame
```


## Creating a store

Using reactive variables is a powerful way to manage state in your Solara applications. However, as your application grows, you may find that you need a more structured way to manage your state.

In larger applications, you may want to create a store to manage your application's state. A store is a regular Python class where all attributes are reactive variables.

In your Python class you are free to expose the reactive variables as attributes, or you can create properties to make certain attributes read-only or to add additional logic when setting an attribute.

A complete TODO application demonstrates this below.

```solara
import uuid
from typing import Callable

import solara


# this todo item is only a collection of reactive values
class TodoItem:
    def __init__(self, text: str, done: bool = False):
        self.text = solara.reactive(text)
        self.done = solara.reactive(done)
        self._uuid = solara.reactive(str(uuid.uuid4()))
        self._dirty = solara.reactive(True)

    def __str__(self) -> str:
        return f"{self.text.value} ({'done' if self.done else 'not done'})"


# However, this class really adds some logic to the todo items
class TodoStore:
    def __init__(self, items: list[TodoItem]):
        # we keep the items as a protected attribute
        self._items = solara.reactive(items)
        self.add_item_text = solara.reactive("")

    @property
    def items(self):
        # and make the items read only for a property
        return self._items.value

    def add_item(self, item):
        self._items.value = [*self._items.value, item]
        # reset the new text after adding a new item
        self.add_item_text.value = ""

    def add(self):
        self.add_item(TodoItem(text=self.add_item_text.value))

    def remove(self, item: TodoItem):
        self._items.value = [k for k in self.items if k._uuid.value != item._uuid.value]

    @property
    def done_count(self):
        return len([k for k in self.items if k.done.value])

    @property
    def done_percentage(self):
        if len(self.items) == 0:
            return 0
        else:
            return self.done_count / len(self.items) * 100


@solara.component
def TodoItemCard(item: TodoItem, on_remove: Callable[[TodoItem], None]):
    with solara.Card():
        solara.InputText("", value=item.text)
        solara.Switch(label="Done", value=item.done)
        solara.Button("Remove", on_click=lambda: on_remove(item))


# The TodoApp component is reusable, so in the future
# we could have multiple TodoApp components if needed
# (e.g. multiple lists of todos)

default_store = TodoStore(
    [
        TodoItem(text="Write a blog post", done=False),
        TodoItem(text="Take out the trash", done=True),
        TodoItem(text="Do the laundry", done=False),
    ]
)


@solara.component
def TodoApp(store: TodoStore = default_store):
    for item in store.items:
        TodoItemCard(item, on_remove=store.remove)

    with solara.Card("New item"):
        solara.InputText(label="Text", value=store.add_item_text)
        solara.Button("Add new", on_click=store.add)
    solara.ProgressLinear(value=store.done_percentage)


@solara.component
def Page():
    TodoApp()
```




## Conclusion
Understanding the advantages and disadvantages of reusable components and application-specific code can help you strike the right balance between modularity and simplicity when building your Solara applications.

By understanding the trade-offs between local and application state, as well as reusable components and application-specific code, you can make better decisions when designing and building your Solara applications. Both approaches have their benefits and drawbacks, but choosing the right method for your specific use case will help you create more efficient, maintainable, and scalable applications.
