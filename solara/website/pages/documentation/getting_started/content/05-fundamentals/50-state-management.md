# Introduction

State management is a crucial aspect of building data-focused web applications with Solara. By effectively managing state, you can create interactive and responsive applications that react to changes in data and user input. In Solara, there are two primary ways to define state: global application state using [`solara.reactive`](/api/reactive) and local component state using [`solara.use_state`](/api/use_state) or [`solara.use_reactive`](/api/use_reactive). This article will discuss these two approaches and provide examples of how to use them in your Solara applications.

## Two main ways of defining state in Solara

### Global application state using solara.reactive

Using [`solara.reactive`](/api/reactive) allows you to create global state variables that can be accessed and modified from any component within your application. This approach is useful when you need to manage state that is shared across multiple components or when you want to maintain consistency throughout your application.

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

## Local component state using solara.use_state

[`solara.use_state`](/api/use_state) is a hook that allows you to manage local state within a specific component. This approach is beneficial when you want to encapsulate state within a component, making it self-contained and modular. Local state management is suitable for situations where state changes only affect the component and do not need to be shared across the application.

Example:
```solara
import solara

@solara.component
def ReusableComponent():
    # color = solara.use_reactive("red")  # another possibility
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

## Local component state using solara.use_reactive


`use_reactive` is the middle ground between `use_state` and `reactive`. It allows you to create a reactive variable that is scoped to a specific component. This is more a matter of taste, we generally recommend using `use_reactive`, but if you prefer a little less magic, you can use `use_state` instead.


If we take the previous example using `use_state`, are replace `use_state` by `use_reactive`, we get:
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

## Conclusion
Understanding the advantages and disadvantages of reusable components and application-specific code can help you strike the right balance between modularity and simplicity when building your Solara applications.

By understanding the trade-offs between local and application state, as well as reusable components and application-specific code, you can make better decisions when designing and building your Solara applications. Both approaches have their benefits and drawbacks, but choosing the right method for your specific use case will help you create more efficient, maintainable, and scalable applications.
