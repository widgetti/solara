# IPywidgets

 * [Documentation](https://ipywidgets.readthedocs.io/en/stable/)
 * [GitHub](https://github.com/jupyter-widgets/ipywidgets)

IPywidgets is a Python library for creating UI objects that live in the Python side *and* on the browser side. They provide bi-directional communication, meaning you can change a slider in the browser, or from the Python side. `IPywidgets` takes care of communication and synchronization.

With ipywidgets you get access to the browser without writing a single line of JavaScript or CSS.


## Solara and ipywidgets

Solara can use almost all existing ipywidgets, from the core library that provides sliders, to [ipyvuetify](./ipyvuetify) which gives us rich UI elements, to ipyvolume that gives us interactive 3d visualizations.

## Where do ipywidgets work?

There are various places where ipywidgets work, and [Solara server](./solara-server) is one of these. There is a [list of frontends that support](https://github.com/jupyter/jupyter/wiki/Jupyter-Widgets#frontends-that-support-jupyter-widgets) meaning that you ipywidgets based applications run
on many places (From Jupyter Notebook, Jupyter Lab, Google Colab to even VS Code).

## Which ipywidget libraries exist?

There is a list [of ipywidget libraries](https://github.com/jupyter/jupyter/wiki/Jupyter-Widgets#custom-jupyter-widgets), but that are probably
many more.


## Do all ipywidget libraries work with Solara server?

All these libraries should work with [Solara server](./solara-server), but we have not tested all of them. If you use a regular ipywidget based app, you should not run into issues. If you do, consider [opening a GitHub issue](https://github.com/widgetti/solara/issues/new)

If you write a Reacton-based Solara application, check out [the reacton page](./reacton).
