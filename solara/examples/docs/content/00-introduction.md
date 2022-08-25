# Introduction


## What is Solara?
Solara lets you use and build reusable UI components for data focussed web apps (data apps) that work in the Jupyter ecosystem and the production ready Solara-server.

Based on proven technologies and mature standards (ReactJS, NextJS, Jupyter, Jupyter-widgets, FastAPI, Flask, etc), Solara will allow your data apps to scale from a one-off experiment in the Jupyter notebook, to a highly dynamic data portal while keeping your code complexity under control.

We care about developer experience, from [hot reloading][/docs/guides/reloading] to type hints and managing complexity.

## Why is Solara build?

Many framework can show you great examples that fit their framework nicely, because they are build to solve a particular problem. However, once you want to create an app that is less simple, or needs to do something slightly different, you hit a wall. Either you find workaround and suffer with horrible code complexities, or if you are out of luck, you cannot build what you want.

The limitations of all the existing frameworks, and the decision to re-invent new ways of binding the Python runtime to the browser, instead of re-using the solid Jupyter and Jupyter-widgets protocol led to the development of Solara.

## How does Solara solve the complexity problem?

Instead of inventing a new API that hopefully solves all problems now and in the future, lets look at the JavaScript world. React is a technology that has proven itself for many years and seems to be an all round good model for building complex UIs.

[React-IPywidgets](https://github.com/widgetti/react-ipywidgets) is the equivalent of ReactJS for Python (and IPywidgets). It allows us to use the same reusable components and hooks as in the ReactJS ecosystem that allows us to build larger web/data application without suffering in complex code bases.

Looking again for at the JavaScript world, we see software such as NextJS is putting a framework around React, to be opinionated and add more "batteries" such as [routing](./understanding/routing).

Solara plays a similar role as NextJS, it build on top of React-IPywidgets, but handles things like routing.

But Solara is also different, it is even more opinionated then NextJS. The reason for this is its focus on the data-heavy Python ecosystem. For this reason it comes with many components and hooks that makes building data apps easier [see the API](/api).

## A quick Solara example

For your understanding, it might be good to just run an example.

Follow the [installation instructions](./installing) or do the TLDR:

    $ pip install solara[server]


Creating a file `myapp.py`, or put the following code in the Jupyter notebook:

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

Solara is actually two things. A server part that takes care of getting the widgets into the browser and a UI part, consisting of react components and hooks.

The UI parts is build on top of [React-IPywidgets](https://github.com/widgetti/react-ipywidgets) which is using the existing IPyWidgets stack.

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
