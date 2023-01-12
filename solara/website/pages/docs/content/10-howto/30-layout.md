# Layouts

Solara will add default [Layout component](/api/default_layout) which includes a navigation sidebar for you automatically.

If you don't want this, you can define your own `Layout` component. The layout component should be
defined in the `__init__.py` file in the same directory, or in the first script. Each subdirectory (or subpackage)
can define its own `Layout` component, which then is embedded into the parent Layout to provide a hierarchical
nested layout tree.


For instance, having no layout gives the same result as putting this `Layout` component in `__init__.py`:
```python
@solara.component
def Layout(children=[]):
    return solara.DefaultLayout(children=children)
```

A possible more custom `Layout` could look like this:

```python
@solara.component
def Layout(children=[]):
    # Note that children being passed here for this example will be a Page() element.
    route_current, routes_all = solara.use_route()
    with solara.VBox() as main:
        with solara.HBox():
            for route in routes_all:
                with solara.Link(route):
                    solara.Button(route.path, color="red" if route_current == route else None)
        solara.VBox(children=children)
    return main
```

See [Understanding Routing](/docs/understanding/routing) for a more in depth documentation on routing.


## Components to use for creating layouts

Layout components are usually constructed using [Container components](/docs/understanding/containers), a few common container components are:

 * [VBox](/api/vbox)
 * [HBox](/api/hbox)
 * [GridFixed](/api/gridfixed)
