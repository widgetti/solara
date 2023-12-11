# Layout

Solara comes with a layout system ideal for data apps.

The following example shows 80% of what you need to know to lay out your app.

```solara
import solara

@solara.component
def Page():
    with solara.Column():
        solara.Title("I'm in the browser tab and the toolbar")
        with solara.Sidebar():
            solara.Markdown("## I am in the sidebar")
            solara.SliderInt(label="Ideal for placing controls")
        solara.Info("I'm in the main content area, put your main content here")
        with solara.Card("Use solara.Columns([1, 2]) to create relatively sized columns"):
            with solara.Columns([1, 2]):
                solara.Success("I'm in the first column")
                solara.Warning("I'm in the second column, I am twice as wide")
                solara.Info("I am like the first column")

        with solara.Card("Use solara.Column() to create a full width column"):
            with solara.Column():
                solara.Success("I'm first in this full with column")
                solara.Warning("I'm second in this full with column")
                solara.Error("I'm third in this full with column")

        with solara.Card("Use solara.ColumnsResponsive(6, large=4) to response to screen size"):
            with solara.ColumnsResponsive(6, large=4):
                for i in range(6):
                    solara.Info("two per column on small screens, three per column on large screens")
```

[Navigate here to watch this layout in a full browser window](/apps/layout-demo)

The key takeaways are:

  * By default, Solara will wrap your component in an [AppLayout](/api/app_layout), which will give you:
    * Room for a sidebar, that you can populate using the [Sidebar](/api/sidebar) component.
    * A toolbar showing the [Title](/api/title).
    * Not visible here: In the case of [multiple pages](/docs/howto/multipage) will include page navigation tabs. See [The multipage demo app](/app/multipage) for an example.
  * Use [Card](/api/card) to put related components together with a title.
  * Use [Column](/api/column) to simply layout components under each other.
  * Use [Columns](/api/columns) if you want to have a few columns with relative sizes next to each other.
  * Use [ColumnsResponsive](/api/columns_responsive) to have the column widths respond to screen size.



## Changing the default layout

While [AppLayout](/api/app_layout) may be sufficient in 80% of the cases. Solara provides a way to change this default layout in [Solara server](/docs/understanding/solara-server).

You can define your own `Layout` component in the `__init__.py` file in the same directory of your app script.


For instance, putting the following `Layout` component in `__init__.py` will give you effectively the same [AppLayout](/api/app_layout):
```python
@solara.component
def Layout(children=[]):
    print("I get called before the Page component gets rendered")
    return solara.AppLayout(children=children)
```


### No Layout
If you do not want to have any layout, you can disable it using:

```python
@solara.component
def Layout(children=[]):
    # there will only be 1 child, which is the Page()
    return children[0]
```

This layout leaves every page responsible for creating its own header, footer, and/or menu structure for navigation.


### Layout with navigation

In case you want to set up your own layout system, which sets up navigation as well, this example may get you started. It may help
to [understand routing](/docs/understanding/routing).
```python
@solara.component
def Layout(children=[]):
    # Note that children being passed here for this example will be a Page() element.
    route_current, routes_all = solara.use_route()
    with solara.Column():
        # put all buttons in a single row
        with solara.Row():
            for route in routes_all:
                with solara.Link(route):
                    solara.Button(route.path, color="red" if route_current == route else None)
        # under the navigation buttons, we add our children (the single Page())
        solara.Column(children=children)
```


### Nested Layouts

Each subdirectory (or subpackage) can define a `Layout` component in its own `__init__.py`, which then is embedded into the parent Layout to provide a hierarchical
nested layout tree.

This is useful for larger apps where each subdirectory may add a bit of layout/chrome around your page.



## Components

The following [Container components](/docs/understanding/containers) can be used to define the layout of you app.

 * [Row](/api/row)
 * [Column](/api/column)
 * [ColumnsResponsive](/api/columns_responsive)
 * [GridFixed](/api/gridfixed)
 * [GridDraggable](/api/griddraggable)
 * [VBox](/api/vbox) (kept for ipywidgets compatibility, please use Column)
 * [HBox](/api/hbox) (kept for ipywidgets compatibility, please use Row)
 * [AppLayout](/api/app_layout) Not often used directly, since Solara will already wrap your page in it. Sometimes re-used in a new `Layout` component.
