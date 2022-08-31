# Introduction


## What is Solara?

Solara lets you use and build data-focused web apps (data apps) using reusable UI components. Your app will work in the Jupyter notebook and production-grade web frameworks (FastAPI, Starlette, Flask, ...).

Solara uses proven technologies and mature standards. Grow from a one-off experiment in the Jupyter notebook to a dynamic data portal in production.  Built on top of React-IPywidgets keeps your code complexity under control.

We care about developer experience. Solara will give your hot code reloading and type hints to faster development.

## Why is Solara created?

How much time have you wasted investing in a web framework only to find out that what you need is impossible to do?

Many frameworks only solve a specific set of problems. Once you step outside of the paved path, you get stuck.

On the other extreme, you might be working with a library with no clear patterns that let you do anything. You may only be weeks away from a total code complexity nightmare, which slowly kills your project.

At the same time, starting a new framework from scratch would be unwise. We prefer to build on top of solid, battle-tested libraries, such as ipywidgets.

## Why use Solara?

Instead of inventing a new API with an unknown track record, we take a different approach. We look at the JavaScript world. React is a technology that has proven itself for many years. It has shown to be an all-around good model for building complex UIs.

React-IPywidgets is the equivalent of ReactJS for Python (and IPywidgets). It allows us to use the same reusable components and hooks as in the ReactJS ecosystem. Using React-IPywidgets, we build web/data applications without suffering from complex code bases.

Looking again at the JavaScript world, we see software such as NextJS is putting a framework around ReactJS. NextJS is more opinionated then ReactJS and adds more "batteries" such as routing.

Solara plays a similar role as NextJS. It builds on top of React-IPywidgets but handles things like routing for you.

But Solara is also different, it is even more opinionated than NextJS. The reason for this is its focus on the data-heavy Python ecosystem. For this reason, it comes with many components and hooks that make building beautiful data apps easier (see our API).

Solara is a clear, systematic, Python-based web framework using industry-trusted technology. Smooth developer experience and enforced code modularity will allow you to build a data app at any scale while maintaining simple code.

## A quick Solara example

For your understanding, it might be good to just run an example.

Follow the [installation instructions](./installing) or do the TLDR:

    $ pip install solara[server]


Create a file `myapp.py`, or put the following code in the Jupyter notebook:

```solara
import react_ipywidgets as react
import solara

@react.component
def Page():
    clicks, set_clicks = react.use_state(0)
    return solara.Button(label=f"Clicked {clicks} times",
                         on_click=lambda: set_clicks(clicks+1))

# in the Jupyter notebook, uncomment the next line:
# display(Page())
```


Run solara-server (if *not* using the Jupyter notebook)

    $ solara run myapp.py
    INFO:     Uvicorn running on http://127.0.0.1:8765 (Press CTRL+C to quit)
    INFO:     Started reloader process [50178] using watchgod
    INFO:     Started server process [50183

The browser should open http://127.0.0.1:8765





## How does Solara fit into the big picture?

Solara is two things. A server part that takes care of getting the widgets into the browser and a UI part, consisting of react components and hooks.

The UI parts are built on top of [React-IPywidgets](https://github.com/widgetti/react-ipywidgets) which is using the existing IPyWidgets stack.

If you use Jupyter, then you probably use the Jupyter notebook, Lab, of Voila to get your widgets into the browser.

If you don't use Jupyter, or don't know what it is, or are a ML Ops, Dev Ops, or Sys Admin, you are probably more interested in the Solara server.

![Solara stack](https://user-images.githubusercontent.com/1765949/168669118-da9410bf-e838-481c-925d-4754efa01b7b.png)

## How do I learn Solara

We recommend going through the [Guides](./guides) documentation first. Feel free to skip chapters, and go back to topics when you need to.

If you want to know what components or hooks are available, check out the [API](/api) which includes live code examples.

[Our examples](/examples) may help you see how particular problems can be solved using Solara, or as inspiration. If you want to contribute an example, reach out to us on GitHub, or direcly open a [Pull Request](https://github.com/widgetti/solara/).


## Where can I hire an expert?

If you need consulting, training or development, you can reach us at:

solara-expert@widgetti.io
