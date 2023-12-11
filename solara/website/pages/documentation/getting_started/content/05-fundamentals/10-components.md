<!-- TODO: column auto -->

# Introduction to Components

In Solara, components are the building blocks of your web application. They allow you to create modular, reusable, and maintainable user interface (UI) elements that can be combined to create a complete and interactive application. Components can range from simple UI elements, such as buttons or text inputs, to more complex and custom visualizations or forms.

The primary benefits of using components in Solara include:

 * Modularity: Components can be designed independently and then combined to form more complex UIs. This modular approach promotes separation of concerns, making it easier to reason about and maintain each part of your application.
 * Reusability: Components can be reused across different parts of your application or even across multiple projects. This can save time and effort by reducing the need to rewrite similar code and can lead to more consistent UIs.
 * Maintainability: By breaking your application into smaller, self-contained components, it becomes easier to understand, debug, and update your code. This results in more maintainable and resilient applications.
 * Performance: When a component instance depends on a specific state, and that state changes, only the render function of the affected component instance will be re-executed. This selective re-rendering ensures that other components or instances that do not depend on the changed state remain unaffected, leading to more efficient performance.

## Types of Components

In Solara, there are two main types of components: Widget Components and Function Components.

## Widget components

Widget Components correspond to ipywidgets and are responsible for rendering visual elements in the browser, such as buttons, sliders, or performing layout tasks. These components are the foundation of your user interface and provide the essential building blocks for creating interactive applications.

Solara mainly uses the [ipyvuetify library](/docs/understanding/ipyvuetify) for its widget components. It provides a set of high-level components that can be used to create rich, interactive user interfaces.

See the [API docs](/docs/api) for a complete list of basic UI components.

## Function Components

Function Components (Components for short), on the other hand, are responsible for combining logic, state, and other components to create more complex and dynamic applications. These components serve as a way to create reusable and modular structures that can be easily integrated into your application.

These are the components that you will be writing when building Solara applications.

By utilizing both Widget Components and Function Components, you can create flexible and powerful applications that provide a rich user experience while maintaining a clean and organized codebase.

## Creating New Components

In Solara, users can create their own custom components without any special distinction from the built-in components provided by the framework, they are all components. These user-defined components have the same capabilities and can be composed seamlessly alongside Solara's components, allowing for the creation of highly customized and reusable user interfaces.

# Defining Components
To create a component in Solara, you'll start by defining a Python function decorated with @solara.component. Inside the function, you can create the component's structure by calling Solara's built-in components or creating custom components to suit your specific needs. If a single element is created, it's taken as the component's main element. If multiple elements are created, they are automatically wrapped in a Column component.

Here's an example of a simple Solara component that displays a button:

```python
import solara

@solara.component
def MyButton():
    solara.Button("Click me!")
```

In this example, we create a component function named MyButton and apply the @solara.component decorator to it. Within the component function, a Button component from Solara is created, displaying the text "Click me!".

## Using Components
Once you've created your components, you can use them in your Solara app by calling the components to create elements. Elements, the lightweight representations of components, can be combined to build complex UIs. They can also be passed as arguments to other components, enabling a flexible and modular application structure.

Here's an example of using the `MyButton` component we defined earlier:

```python
import solara

@solara.component
def MyApp():
    MyButton()
    MyButton()
```

In this example, we create a `MyApp` function decorated with `@solara.component`. The function create two MyButton elements, resulting in two buttons (or two component instances).

## Handling User Interactions
Components in Solara can capture user input and respond to events, such as button clicks or form submissions. To handle user interactions, you'll define callback functions and connect them to your components using Solara's event handling system.

Here's an example of a Solara component that displays a button and responds to click events:

```python
import solara

def on_button_click(event):
    print("Button clicked!")

@solara.component
def MyInteractiveButton():
    solara.Button("Click me!", on_click=on_button_click)
```

In this example, we define a function called on_button_click that will be executed when the button is clicked. In the MyInteractiveButton function, we create a Button component and set the on_click argument to the on_button_click function.

By following these steps, you can create and use components to build rich, interactive applications with Solara.


## Component Arguments and State
In Solara, components can accept arguments and maintain internal state to manage their behavior and appearance. This section will explain how to use arguments and state in your Solara components and provide code examples to demonstrate their usage.

### Component Arguments
Arguments are the values that you pass to a component when you call it, allowing you to customize its behavior and appearance. You can define the arguments your component accepts by specifying them as parameters in the component function. This makes your components more reusable and flexible, as you can easily modify their behavior by passing different argument values.

Here's an example of a Solara component that accepts an argument:

```python
import solara

@solara.component
def MyButton(text):
    solara.Button(text)
```

In this example, we define a function called MyButton that takes a single argument, text. The render function creates a Button component from Solara with the specified text.

### Using Application state in Components
To manage the state of a component in Solara, you can use the solara.reactive() function to create reactive variables. Reactive variables are used to store values that can change over time and automatically trigger component updates when their values change. This allows you to create components that respond to changes in data and user interactions.

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

In this example, we create a reactive variable counter with an initial value of 0. We define two components: `CounterDisplay` and `IncrementButton`. `CounterDisplay` renders the current value of counter, while `IncrementButton` increments the value of counter when clicked. Whenever the counter value changes, `CounterDisplay` automatically updates to display the new value.

By using arguments and state in your Solara components, you can create more dynamic and interactive applications that respond to user input and changes in data.

### Internal State in Components

In addition to using reactive variables for global or application-wide state, you can also manage internal or component-specific state using the use_state hook in Solara. The use_state hook allows you to define state variables that are local to a component, and automatically trigger updates when their values change.

To use the use_state hook, call the solara.use_state() function inside your component function. This function takes an initial value as an argument and returns a tuple containing the current state value and a function to update the state.

Here's an example that demonstrates the use of the use_state hook to manage internal state in a Solara component:

```solara
import solara

@solara.component
def Counter():
    count, set_count = solara.use_state(0)

    def increment():
        set_count(count + 1)

    solara.Button("Increment", on_click=increment)
    solara.Info(f"Counter: {count}")

@solara.component
def Page():
    Counter()
```

In this example, we define a Counter component that uses the use_state hook to manage its internal state. We create a state variable count with an initial value of 0 and a function set_count to update the state. The increment function increments the value of count when the button is clicked. Whenever the count value changes, the component automatically updates to display the new value.

By using the use_state hook, you can manage the internal state of your components and create more dynamic and interactive applications that respond to user input and changes in data.

## Lazy Rendering in Solara Components

In Solara, understanding the relationship between components, elements, and instances is essential to grasp the rendering process. Components serve as a blueprint or template for defining the structure and behavior of a part of the user interface. Elements are lightweight virtual representations of components, created when the components are invoked. Instances, on the other hand, represent the function body of the component and its state.

Solara employs a "lazy rendering" approach, where the rendering of a component's children is deferred until it is necessary. When a component is invoked, an element is created immediately, representing that particular instance of the component. However, the actual rendering of the component's children is postponed until the component is rendered within the virtual tree, either as a child of another component or as the root component. This allows Solara to optimize the rendering process and update only the necessary components when the application state or component arguments change.

Lazy rendering in Solara ensures that the render function is executed only when necessary, improving the application's performance. To illustrate this concept, let's consider the following example:


```solara
import solara

counter = solara.reactive(0)

@solara.component
def CounterDisplay():
    solara.Info(f"Counter: {counter.value}")

@solara.component
def IncrementButton():
    def increment():
        counter.value += 1

    solara.Button("Increment", on_click=increment)

@solara.component
def RandomText():
    import random
    solara.Info(f"Random number: {random.random()}")

@solara.component
def Page():
    IncrementButton()
    CounterDisplay()
    RandomText()
```

In this example, we define several components: `IncrementButton`, `CounterDisplay`, and `RandomText`. The `IncrementButton` component increments the value of the counter reactive variable when clicked. The `CounterDisplay` component displays the current value of the counter. The `RandomText` component displays a random number but does not depend on any state or reactive variables.

When the user clicks the `IncrementButton`, the counter reactive variable is updated, and the `CounterDisplay` component re-renders to show the new value. The RandomText component does not re-render in this scenario because it does not depend on any state or reactive variables.

This example demonstrates Solara's lazy rendering, where only the relevant components are instantiated and rendered based on changes in their arguments or internal state. This ensures that the render function is executed only when necessary, improving the application's performance.


## Conclusions
In conclusion, understanding components, their arguments, and how to manage their internal state is crucial for building Solara applications. To create more advanced components, you need to have a deeper understanding of hooks, such as the use_state hook we have already discussed.

In the next fundamentals article, we will explore more hooks available in Solara, which will enable you to build more sophisticated components that cater to a wide range of use cases. By learning about hooks, you can create powerful components that can manage state, interact with other components, and respond to user input.

To summarize, components are the building blocks of Solara applications, and they can accept arguments to customize their behavior and appearance. Managing state in components can be done either through local (component) state or application-wide state, each with its advantages and disadvantages. By striking a balance between reusable components and application-specific code, you can create scalable and maintainable applications in Solara. With a solid understanding of components and their state management, you are well on your way to creating powerful and interactive web applications with Solara.
