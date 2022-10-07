# Laying out components

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
    return solara.HBox(children=[button_increase,
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

    with solara.HBox() as main:
        solara.Button(label=f"Clicked: {clicks}", on_click=increase_count)
        solara.Button(label="Reset", on_click=reset_count)
    return main

Page = FancyClickButton

```

Here we are using the top-level HBox as a context manager (with the name `main`). All child elements created within this context are automatically added as a child. The exception is that the element should not be added manually as child to another element.


### Nested layout

Adding children using context managers work at any level, you can nest HBoxes and VBoxes [or any other containers](/api#layout).


```solara
import solara


@solara.component
def FancyClickButton():
    clicks, set_clicks = solara.use_state(0)

    def increase_count():
        set_clicks(clicks + 1)

    def reset_count():
        set_clicks(0)

    with solara.VBox() as main:
        with solara.HBox():
            solara.Button(label=f"Clicked: {clicks}", on_click=increase_count)
            solara.Button(label="Reset", on_click=reset_count)
        solara.Text("I am a child of a VBox")
    return main

Page = FancyClickButton

```
