# Introduction


## What is Solara?

Solara is an Open Source library that lets you use and build data-focused web apps (data apps) using reusable UI components. Your app will work in the Jupyter notebook and production-grade web frameworks (FastAPI, Starlette, Flask, ...).

Solara uses proven technologies and mature standards. Grow from a one-off experiment in the Jupyter notebook to a dynamic data portal in production.  Built on top of [Reacton](/docs/understanding/reacton) to keep your code complexity under control and [IPywidgets](/docs/understanding/ipywidgets) to access a rich set of UI libraries without having to write Javascript or CSS.

We care about developer experience. Solara will give your hot code reloading and type hints for faster development.

## Why is Solara created?

How much time have you wasted investing in a web framework only to find out that what you need is impossible to do?

Many frameworks only solve a specific set of problems. Once you step outside of the paved path, you get stuck.

On the other extreme, you might be working with a library with no clear patterns that let you do anything. You may only be weeks away from a total code complexity nightmare, which slowly kills your project.

At the same time, starting a new framework from scratch would be unwise. We prefer to build on top of solid, battle-tested libraries, such as [IPywidgets](/docs/understanding/ipywidgets).

## Why use Solara?

Instead of inventing a new API with an unknown track record, we take a different approach. We look at the JavaScript world. React is a technology that has proven itself for many years. It has shown to be a good all-around model for building complex UIs.

[Reacton](/docs/understanding/reacton) is the equivalent of ReactJS for Python (and IPywidgets). It allows us to use the same reusable components and hooks as in the ReactJS ecosystem. Using Reacton, we build web/data applications without suffering from complex code bases.

Looking again at the JavaScript world, we see software such as NextJS is putting a framework around ReactJS. NextJS is more opinionated than ReactJS and adds more "batteries" such as routing.

Solara plays a similar role as NextJS. It builds on top of Reacton but handles things like routing for you.

But Solara is also different and is even more opinionated than NextJS. The reason for this is its focus on the data-heavy Python ecosystem. For this reason, it comes with many components and hooks that make building beautiful data apps easier (see our [API](/api)).

Solara is a clear, systematic, Python-based web framework using industry-trusted technology. Smooth developer experience and enforced code modularity will allow you to build a data app at any scale while maintaining simple code.

## A quick Solara example

For your understanding, it might be good just to run an example.

Follow the [installation instructions](/docs/installing) or do the TLDR:

    $ pip install solara


Create a file `myapp.py`, or put the following code in the Jupyter notebook:

```solara
import solara

clicks = solara.reactive(0)


@solara.component
def Page():
    def increase_clicks():
        clicks.value += 1

    solara.Button(label=f"Clicked {clicks} times", on_click=increase_clicks)

# in the Jupyter notebook, uncomment the next line:
# display(Page())
```

*Note that the above output is __live__, you can click the button and see the behaviour*.

Run solara-server (if *not* using the Jupyter notebook)

    $ solara run myapp.py
    Solara server is starting at http://localhost:8765

The browser should open http://127.0.0.1:8765




## How does Solara fit into the big picture?

Solara is actually two things.

### Solara server
[Solara server](/docs/understanding/solara-server) renders ipywidgets in the browser in a very efficient manner and takes care of many other things
such as [routing](/docs/understanding/routing) and [Static Site Generation](/docs/reference/static-site-generation).

### Solara UI

The UI part is built on top of [Reacton](/docs/understanding/reacton), which uses the existing IPyWidgets stack. It gives a consistent set
of modern UI components with the Material Design look, as well as a set of routines to make application development of data heavy web apps
easier.


### Overview
If you use Jupyter, then you probably use the Jupyter notebook, Lab, or [Voila](/docs/understanding/voila) to get your widgets into the browser. You may not care about [Solara server](/docs/understanding/solara-server) and can focus on just the UI part.

If you don't use Jupyter, don't know what it is, or are an ML Ops, Dev Ops, or Sys Admin, you are probably more interested in the Solara server.

![Solara stack](https://dxhl76zpt6fap.cloudfront.net/public/docs/solara-stack.webp)

## How do I learn Solara?

We recommend going through the documentation linearly following the arrows on the bottom, meaning you will go through:

 * [Installing](/docs/installing)
 * [Quick start](/docs/quickstart)
 * [Tutorials](/docs/tutorial)

If you want to know more about specific parts, you can go through the [How-to section](/docs/howto) to learn more. Feel free to skip chapters, and go back to topics when you need to.


If you want to know what components or hooks are available, or want to know more about a specific component, check out the [API](/api) which includes live code examples. Other reference documentation can be found at the [reference section](/docs/reference)

If you feel like you miss some basic understanding and want to give a bit deeper into the what and why feel free to explore the [Understanding section](/docs/understanding).


[Our examples](/examples) may help you see how particular problems can be solved using Solara, or as inspiration. If you want to contribute an example, contact us on GitHub or directly open a [Pull Request](https://github.com/widgetti/solara/).


## Where can I hire an expert?

If you need consulting, training or development, you can reach us at:

contact@solara.dev
