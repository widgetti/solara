# Layouts

Solara will add default [Layout component](/api/default_layout) which includes a navigation sidebar for you automatically.

If you don't want this, you can define your own `Layout` component. The layout component should be
defined in the `__init__.py` file in the same directory, or in the first script. Each subdirectory (or subpackage)
can define its own `Layout` component, which then is embeded into the parent Layout to provide a hierarchical
nested layout tree,.


For instance, having no layout gives the same result as putting this `Layout` component in `__init__.py`:
```python
@react.component
def Layout(children=[]):
    return sol.DefaultLayout(children=children)
```

A possible more custom `Layout` could look like this:

```python
@react.component
def Layout(children=[]):
    # Note that children being passed here for this example will be a Page() element.
    route_current, routes_all = sol.use_route()
    with sol.VBox() as main:
        with sol.HBox():
            for route in routes_all:
                with sol.Link(route):
                    sol.Button(route.path, color="red" if route_current == route else None)
        sol.VBox(children=children)
    return main
```

See [Understanding Routing](/docs/understanding/routing) for a more in depth documentation on routing.
