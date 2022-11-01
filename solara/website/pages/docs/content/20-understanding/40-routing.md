# Routing

Routing takes care of linking a web address (more specifically the [pathname](https://developer.mozilla.org/en-US/docs/Web/API/Location), e.g. "/docs/basics/solara") to a state of the UI,
usually in the form of what appears as pages to a user.


Routing includes navigation (hitting the back and forward button of your browser) without causing a page reload.


## Automatic routing

Setting up routing can be repetative, and thefore Solara comes also with a more opinionated method for setting up routing automatically.

### Based on a directory

Using [`generate_routes_directory(path: Path) -> List[solara.Route]:`](/api/generates_routes_directory) we can request Solara to give us a list of
routes by scanning a directory for Python scripts, Notebooks and Markdown files.

This function is being used by Solara if you run solara server with a directory as argument name, as used in [Getting Started/Multiple Pages](../getting-started/multiple-pages). More details can be found there.


### Based on a Python package

Similar to the previous section [`generate_routes(module: ModuleType) -> List[solara.Route]:`](/api/generates_routes) will return a list of routes by scanning a Python package or module for `Page` components, or `app` elements. Again, more information can be found at [Getting Started/Multiple Pages](../getting-started/multiple-pages).

## Manually defining routes

In Solara, we set up routing by defining a list of `solara.Route` objects, where each route can have another list of routes, its children, forming
a tree of routes. We assign this list to the `routes` variable in your main app script or module, so Solara can find it and it should be in the same namespace as your `Page` component.

Routes are matched by splitting the pathname around the slash ("/") and matching each part to the routes.

An example route definition could be something like this:

```python
import solara as sol

routes = [
    # route level == 0
    solara.Route(path="/"),  # matches empty path ''
    solara.Route(
        # route level == 1
        path="docs",  # matches '/docs'
        children=[
            # route level == 2
            solara.Route(path="basics", children=[  # matches '/docs/basics'
                # route level == 3
                solara.Route(path="react"),      # matches '/docs/basics/react'
                solara.Route(path="ipywidgets"), # matches '/docs/basics/ipywidgets'
                solara.Route(path="solara"),     # matches '/docs/basics/solara'
            ]),
            solara.Route(path="advanced")  # matches '/docs/advanced'
        ],
    ),
    solara.Route(
        path="blog",
        # route level == 1
        children=[
            solara.Route(path="/"),   # matches '/blog'
            solara.Route(path="foo"), # matches '/blog/foo'
            solara.Route(path="bar"), # matches '/blog/bar'
        ],
    ),
    solara.Route(path="contact")  # matches '/contact'
]

@reacton.component
def Page():
    ...
```

The level of the depth into the tree is what we call the `route_level`, which starts at 0, the top level.
Each call to `use_route` will return the current route (if there is a match to the current path) and the list of siblings including itself.

## Rendering based on routes

For instance, when our pathname is `/docs/basics/react`, the following code shows what
`solara.use_route_level` and `solara.use_route` will return:

```python
@reacton.component
def MyRootComponent():
    level = solara.use_route_level()  # returns 0
    route_current, routes_current_level = solara.routes()
    # route_current is routes[1], i.e. solara.Route(path="docs", children=[...])
    # routes_current_level is [routes[0], routes[1], routes[2], routes[3]], i.e.:
    #    [solara.Route(path="/"), solara.Route(path="docs", children=[...]),
    #     solara.Route(path="blog", children=[...]), solara.Route(path="contact")]
    if route_current is None: # no matching route
        return solara.Error("oops, page not found")
    else:
        # we could render some top level navigation here based on route_current_level and route_current
        return MyFirstLevelChildComponent()


@reacton.component
def MyFirstLevelChildComponent():
    level = solara.use_route_level()  # returns 1
    route_current, routes_current_level = solara.routes()
    # route_current is routes[1].children[0], i.e. solara.Route(path="basics", children=[...])
    # routes_current_level is [routes[1].children[0], routes[1].children[1]], i.e.:
    #    [solara.Route(path="basics", children=[...]), solara.Route(path="advanced")]
    if route_current is None: # no matching route
        return solara.Error("oops, page not found")
    else:
        # we could render some mid level navigation here based on route_current_level and route_current
        return MySecondLevelChildComponent()

@reacton.component
def MySecondLevelChildComponent():
    level = solara.use_route_level()  # returns 2
    route_current, routes_current_level = solara.routes()
    # route_current is routes[1].children[0].children[0], i.e. solara.Route(path="react")
    # routes_current_level is [routes[1].children[0].children[0], routes[1].children[0].children[1], routes[1].children[0].children[2]], i.e.
    #    [solara.Route(path="react"), solara.Route(path="ipywidgets"), solara.Route(path="solara")]
    if route_current is None: # no matching route
        return solara.Error("oops, page not found")
    else:
        # we could render some mid level navigation here based on route_current_level and route_current
        if route_current.path == "react":
            return DocsBasicReact()  # render the actual content
        elif route_current.path == "ipywidgets":
            return DocsBasicIpyWidgets()
        elif route_current.path == "solara":
            return DocsBasicSolara()
        else:
            return solara.Error("oops, not possible!")

```

From this code, we can see we are free how we transform the routes into the state of the UI (i.e. which components are rendered).

## Adding data

Often, your render logic needs some extra data on what to display. For instance, you may want to dynamically render tabs based on the routes,
which requires you to have a label, and know which component to add.
For this purposed we added `label: str` and the `component' attributes, so you can defines routes likes:
```
routes = [
    solara.Route("/", component=Home, label="What is Solara ☀️?"),
    solara.Route("docs", component=docs.App, label="Docs", children=docs.routes),
    solara.Route(
        "demo",
        component=demo.Demo,
        children=demo.routes,
        label="Demo",
    ),
    ...
]
```

If you need to store more data in the route, you are free to put whatever you want in the `data` attribute, see also [Route](/api/route).



## Linking

Note that all routes are relative, since a component does not know if it is embedded into a larger application, which may also do routing.


Therefore you should never use the `route.path` for navigation since the route object has no knowledge of the full url
(e.g. `/docs/basics/ipywigets`) but only knows its small piece of the pathname (e.g. `ipywidgets`)

Using [`resolve_path`](/api/resolve_path) we can request the full url for navigation.

```python
def resolve_path(path_or_route: Union[str, solara.Route], level=0) -> str:
    ...
```

We can pass this full URL to the [`solara.Link`](/api/link) component, e.g. like:

```python
@reacton.component
def LinkToIpywidgets():
    route_ipywidgets = routes.children[1].children[0].children[1]
    # route_ipywidgets.path == "ipywidgets"
    path = solara.resolve_path(route_ipywidgets)
    # path == '/docs/basics/ipywidgets
    with solara.Link(path) as main:
        solara.Button("read about ipywidgets")
    return main
```
