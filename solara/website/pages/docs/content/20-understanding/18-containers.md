# Laying out components with containers

## Introduction
Some components, such as our favorite `ClickButton` only add logic on top of an existing component:

```solara
import solara


@solara.component
def ClickButton():
    clicks, set_clicks = solara.use_state(0)

    def my_click_hander():
        set_clicks(clicks + 1)

    # We return a single component
    return solara.Button(label=f"Clicked: {clicks}", on_click=my_click_hander)

Page = ClickButton
```


## Containers with children
However, more sophisticated components will add multiple components together into a container component, let's take a look at an example.

```solara
import solara


@solara.component
def FancyClickButton():
    clicks, set_clicks = solara.use_state(0)

    def increase_count():
        set_clicks(clicks + 1)

    def reset_count():
        set_clicks(0)

    button_increase = solara.Button(label=f"Clicked: {clicks}", on_click=increase_count)
    button_reset = solara.Button(label="Reset", on_click=reset_count)

    return solara.Row(children=[button_increase,
                                 button_reset,
                                 ])


Page = FancyClickButton

```


Here we use an [HBox](/api/hbox) to lay out two child components horizontally.


## Cleaner way to add children to containers

Because using container components is so common, we created a more convenient way to pass children to components and made your code look neater and more structured as well (avoiding nested lists).

```solara
import solara


@solara.component
def FancyClickButton():
    clicks, set_clicks = solara.use_state(0)

    def increase_count():
        set_clicks(clicks + 1)

    def reset_count():
        set_clicks(0)

    with solara.Row() as main:
        solara.Button(label=f"Clicked: {clicks}", on_click=increase_count)
        solara.Button(label="Reset", on_click=reset_count)
    return main

Page = FancyClickButton

```

Here we are using the top-level Row as a context manager (with the name `main`). All child elements created within this context are automatically added as a child.

### About Context managers

Context managers are a Python language feature, there are two ways to use them:

```python

with some_anonymous_context_manager():
    print("some code")

with some_named_context_manager() as this_is_my_name:
    print("some other code")
```

Where the last example assigns the context manager to a variable. In Solara we only need to do that to the top context manager, since we need to return that in our [render function](/docs/understanding/anatomy).

All Reacton or Solara components return elements that can be used as context managers. Context managers allow for code to be executed before and after your code block inside of the context manager. This allows us to capture all elements created inside of the context manager. If you want to know more about context managers, consult the Python documentation since this is not Solara specific.


### Nested layout

Adding children using context managers work at any level, you can nest Rows and Columns [or any other containers](/api#components).


```solara
import solara


@solara.component
def FancyClickButton():
    clicks, set_clicks = solara.use_state(0)

    def increase_count():
        set_clicks(clicks + 1)

    def reset_count():
        set_clicks(0)

    with solara.Column() as main:
        with solara.Row():
            solara.Button(label=f"Clicked: {clicks}", on_click=increase_count)
            solara.Button(label="Reset", on_click=reset_count)
        solara.Text("I am a child of a VBox")
    return main

Page = FancyClickButton

```


## Automatic containers


Instead of returning the main container, Solara also allows you to not have a return value (or return `None`).
If that is the case, Solara will look at what elements you created. If you created one, that element will be taken
as a return value instead. If you make more than one element, those elements will be automatically wrapped by
a [Column](/api/column). The only benefit of returning an element, is that we can infer the correct return type,
which can be useful for testing purposes. Users should probably never return an element, but use the automatic
container feature.

```solara
import solara


@solara.component
def ClickButton():
    clicks, set_clicks = solara.use_state(0)

    def my_click_hander():
        set_clicks(clicks + 1)

    solara.Button(label=f"Clicked: {clicks}", on_click=my_click_hander)
    solara.Button(label=f"Reset", on_click=lambda: set_clicks(0))

Page = ClickButton
```
