# Making new components

When starting with solara, you will always create a `Page` component. This `Page` component will be using components provided by solara.

When your project grows, you might build your own reusable components [as described in the fundamentals](https://solara.dev/documentation/getting_started/fundamentals/components).

Depending on your needs, this may not be sufficient, and there are several approaches to creating new components:

## Build a Pure Python component using ipyvuetify

Most components in Solara itself are build on top of [Vuetify](https://v2.vuetifyjs.com/), using the [ipyvuetify](/documentation/advanced/understanding/ipyvuetify) Python binding.

If there is a component in [Vuetify](https://v2.vuetifyjs.com/) that you want to use that is not (yet) exposed in Solara directly, you can access
all the components via [ipyvuetify](/documentation/advanced/understanding/ipyvuetify).


## Build a Frontend component

Sometimes it is beneficial to build a component directly in the frontend. This are several reasons for this:

 * Lower latency/performance: If a component is very performance-critical, it might be beneficial to build it in the frontend as it does not require a roundtrip to the server.
 * Direct access to the DOM: If you need to interact with the DOM directly, it might be beneficial to build a component in the frontend.
 * Simpler: Sometimes it is just simpler to build a component in the frontend and Solara.
 * Use of third-party libraries: If you want to use a third-party library that is not available in Solara, you can build a component in the frontend.


### Using Vue

In solara itself, we use Vue to write new frontend components. The main reason is that we build Solara on top of [Vuetify](https://v2.vuetifyjs.com/), which is a Vue component library.

Vue is easy to use for non-front-end developers, and it is easy to learn and is the default option for the Solara dev itself. No frontend tools are needed (like webpack, etc.), and you can write your components directly in file or inline string in python.

The downside of using Vue, is that we are currently limited to Vue 2, and our ipyvue library has no support for ESM modules, introducing a bit of boilerplate code
to load external libraries.

[Explore how to use a new Vue component in Solara, in our dedicated Howto](/documentation/advanced/howto/make-a-vue-component).


### Using React

Since the release of [ipyreact](https://github.com/widgetti/ipyreact/) we can now also very easily write write ReactJS components for Solara.
ReactJS has the advantage that its model is quite similar to Solara itself, and it is very popular in the frontend world with a ton of third
party libraries available.

Another advantage is the ipyreact supports ESM modules, so you can directly use third party libraries without any boilerplate code.
This library also allows sharing of ESM modules between different widgets, and composition of widgets (i.e. having child widgets).

[Explore how to use a new React component in Solara, in our dedicated Howto (SOON)](/documentation/advanced/howto/make-a-react-component).

### Using Javascript

If you prefer to use pure JavaScript (actually TypeScript), you can [write you own widget](https://github.com/jupyter-widgets/widget-ts-cookiecutter), but this requires
a lot of work. This will give you however, the most flexibility. The underlying libraries mentioned above (ipyreact and ipyvue) are build on top of this.

[AnyWidget](https://anywidget.dev/) has a similar solution to ipyvue and ipyreact, but is targeted at pure JavaScript. It's a well documented project, and in most
cases a better alternative to writing your own ipywidget from scratch.

AnyWidget support ESM modules, but has no native way to re use ESM modules between different widgets or composition of widgets.

[Explore how to use a new JS component in Solara, in our dedicated Howto (SOON)](/documentation/advanced/howto/make-a-javascript-component).
