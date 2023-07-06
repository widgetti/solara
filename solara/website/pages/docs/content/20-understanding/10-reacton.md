# Reacton

 * [Documentation](https://reacton.solara.dev/)
 * [GitHub](https://github.com/widgetti/reacton/)

Reacton is a React-like layer around ipywidgets.

Using a declarative way, in a React (JS) style, makes your codebase smaller, less error-prone, and easier to reason about. We don't see a good reason not to use it.

Also, React has proven itself, and by adopting a proven technology, we can stand on the shoulders of giants, make use of a lot of existing resources, and do not have to reinvent the wheel.


## Solara or Reacton?

We consider Solara a superset of Reacton, and that's why the full namespace of the `reacton` package is imported into the `solara` package.
Therefore, you can write `solara.use_state` or `reacton.use_state`, they are the same function.

The reason for this is simplicity for newcomers, who don't care about the difference between `solara` and `reacton`.
But in practice, it also saves having to import both `solara` and `reacton`.
Also, when writing Solara based apps, one does not think about Reacton anymore, it is all Solara.

## How do I use Reacton or Solara with ipywidget library X

[The reacton documentation has a page on this](https://reacton.solara.dev/en/latest/libraries/)
