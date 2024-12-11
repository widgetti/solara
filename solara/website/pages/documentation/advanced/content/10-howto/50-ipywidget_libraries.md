---
title: Using various ipywidgets libraries within a Solara application
description: Solara can work with virtually any ipywidget library, and enables powerful interactivity with libraries like ipyleaflet, ipydatagrid, and bqplot.
---
# How can I use ipywidget library X?

Solara can work with any ipywidget library, such as [ipyleaflet](https://github.com/jupyter-widgets/ipyleaflet), [ipydatagrid](https://github.com/bloomberg/ipydatagrid) or [bqplot](https://github.com/bqplot/bqplot).

After `solara` is imported, every widget class has an extra `.element(...)` method added to itself. This allows us to create elements for all existing widgets. For example using regular ipywidgets:

```python
import ipywidgets
button_element = ipywidgets.Button.element(description="Click me")
```

## Example with ipyleaflet

For instance, if we want to use ipyleaflet using the classical ipywidget API, we can do:

```python
import ipyleaflet

map = ipyleaflet.Map(center=(52, 10), zoom=8)

marker = Marker(location=(52.1, 10.1), draggable=True)
m.add_layer(marker)
```

In Solara, ideally, we should not create widgets, but elements instead. We can create elements using the `.element(...)` method. This method takes the same arguments as the widget constructor, but returns an element instead of a widget. The element can be used in the same way as a widget, but it is not a widget. It is a special object that can be used in Solara.

However, how do we add the marker to the map? The map element object does not have an `add_layer` method. That is the downside of using the React-like API of Solara. We cannot call methods on the widget
anymore. Instead, we need to pass the marker to the layers argument. That, however, introduces a new problem. Ipyleaflet by default adds a layer to the map when it is created, and the `add_layer` adds the second layer. We now need to manually add the map layer ourselves.

Putting this together.
```solara
import ipyleaflet
import solara

url = ipyleaflet.basemaps.OpenStreetMap.Mapnik["url"]

@solara.component
def Page():
    marker = ipyleaflet.Marker.element(location=(52.1, 10.1), draggable=True)
    map = ipyleaflet.Map.element(
        center=(52, 10),
        zoom=8,
        layers=[
            ipyleaflet.TileLayer.element(url=url),
            marker,
        ],
    )
```

Note that this is about the worst example of something that looks easy in ipyleaflet using the classical API becoming a bit more involved in Solara.
In practice, this does not happen often, and your code in general will be shorter and more readable.

Another thing of note is that ipyleaflet uses CSS `z-index` to layer content, potentially causing issues with your map overlaying other content. This can be avoided by styling the parent element of the map with `isolation: isolate;`. For examples of how to do this, you can see the below examples.

See also [the basic ipyleaflet example](/examples/libraries/ipyleaflet) and [the advanced ipyleaflet example](/examples/libraries/ipyleaflet_advanced).

## Example with ipywidgets

Most widgets in (classic) ipywidgets can be used without problems in Solara. Two widgets stand out that are difficult to use.

### Image

The `Image` widget can be used normally, but we cannot use the factory methods like `Image.from_file` and `Image.from_url`, for this reason we create the [Image](/api/image) component that
makes this easier.

### Video

The `Video` widget does not have a corresponding component in solara (yet), but we can manually fill in the `value`. For example:

```solara
import solara
import ipywidgets

url = 'https://user-images.githubusercontent.com/1765949/240697327-25b296bd-72c6-4412-948b-2d37e8196260.mp4'


@solara.component
def Page():
    ipywidgets.Video.element(value=url.encode('utf8'),
        format='url',
        width=500
    )

```

## Escape hatch

Some libraries do not give access to the widget classes, or wrap the creation of widgets into a function making it impossible to create an element.

### Quick and bad way

If you quickly want to show a widget in your prototype, and want to avoid all the boilerplate at the
cost of a bit of a memory leak, use the following technique.

Here we directly create a widget in the render function instead of indirectly via an element.
Since only elements get automatically added to its parent component, so we need to manually
call [display](/api/display).

```solara
import solara
import ipywidgets as widgets


@solara.component
def Page():
    button_widget = widgets.Button(description="Classic Widget")
    solara.display(button_widget)

    def change_description(btn):
        button_widget.description = "Great escape hatch"
    button_widget.on_click(change_description)
```

With this approach, there are two issues. First, we do not clean up the widget we created by calling `.close()` on it. Although
we can do that in the cleanup function of a [use_effect](/api/use_effect), in some situations the render function can be called,
without calling the use_effect.

The second issue is that every time to component gets rerendered (argument change, or state changes
like a reactive variable it depends on) it will re-create the widget.

This last issue is demonstrated in this example. We modify the above example by adding an extra state change (modifying the
`if_i_change_we_recreate_the_widget` reactive variable) that causes the button to be completely re-created, resetting the description.

```solara
import solara
import ipywidgets as widgets


@solara.component
def Page():
    if_i_change_we_recreate_the_widget = solara.use_reactive(0)
    print("if_i_change_we_recreate_the_widget", if_i_change_we_recreate_the_widget.value)

    button_widget = widgets.Button(description="Classic Widget")
    solara.display(button_widget)


    def change_description(btn):
        # this 'works'
        button_widget.description = "Great escape hatch"
        # but because this will trigger a re-render, it will
        # re-create the widget
        if_i_change_we_recreate_the_widget.value += 1
    # Now we can call normal functions on it
    button_widget.on_click(change_description)
```

### Proper way

If you want to have more control on when your widgets gets created (only once for instance), and how to clean it up, uou can use the the following general pattern,
here demonstrated using an ipywidget Button:

```solara
import solara
import ipywidgets as widgets


@solara.component
def Page():
    if_i_change_we_rerender = solara.use_reactive(0)
    # Important to use a widget component, not a function component,
    # otherwise the children will be reset after we change it in the
    # use_effect function.
    container = solara.v.Html(tag="div")
    # Because of this, this container will not work:
    # container = solara.Column()

    def add_classic_widget():
        # generate your normal widget
        button_widget = widgets.Button(description="Classic Widget")

        def change_description(btn):
            button_widget.description = "Proper escape hatch"
            # This will trigger a rerender, but not re-execute the use_effect
            if_i_change_we_rerender.value += 1
        # Now we can call normal functions on it
        button_widget.on_click(change_description)

        # add it to the generated widget by solara/reacton
        container_widget = solara.get_widget(container)
        container_widget.children = (button_widget,)

        def optional_cleanup():
            # ideally, we cleanup the widgets we created.
            # If you skip this step, the widgets will be garbage collected
            # when the solara virtual kernel gets closed.
            # In the Notebook or Voila skipping this step can cause a (small)
            # memory leak.
            container_widget.children = ()
            button_widget.on_click(change_description, remove=True)
            button_widget.layout.close()
            button_widget.style.close()
            button_widget.close()
        return optional_cleanup

    solara.use_effect(add_classic_widget, dependencies=[])

    # We could potentially update the button based on if_i_change_we_rerender using:
    # solara.use_effect(update_button, dependencies[if_i_change_we_rerender.value])
    # However, getting a reference to the widget is a bit trickier, use solara.use_ref
    # https://reacton.solara.dev/en/latest/api/#use_ref would come handy, e.g.
    # button = solara.use_ref(None)
    # And assign button.current in the add_classic_widget function and access
    # if in other use_effects
    return container
```



## ipyaggrid

[IPyAgGrid](https://github.com/widgetti/ipyaggrid) has the disadvantage that the constructor arguments
are not the same as the traits or property names on the object. For instance, when calling the
Grid constructor, `grid_data` is used, while updating the dataframe goes via [`.update_grid_data(...)`](https://widgetti.github.io/ipyaggrid/guide/create.html#update-data)


```python
import ipyaggrid
grid = ipyaggrid.Grid(grid_data=df)
...
grid.update_grid_data(df_other)
```

When using solara/reacton components, we do not create widgets directly, but prefer to use elements (descriptions of component instances)
to get lifetime management, and automatic updates of traits. This automatic updating of traits however, does not work in this case,
since it should call `.update_grid_data(...)` instead.

To get around this, we can again use `use_effect` whenever the dataframe (or other state that signals a change in the dataframe) changes.

```solara
from typing import cast
import ipyaggrid
import plotly.express as px
import solara


df = px.data.iris()
species = solara.reactive("setosa")


@solara.component
def Page():
    df_filtered = df.query(f"species == {species.value!r}")
    solara.Select("Filter species", value=species, values=["setosa", "versicolor", "virginica"])

    # does NOT update aggrid when grid_data argument changes
    # since grid_data is not a trait, so letting reacton/solara update this property has no effect
    grid = ipyaggrid.Grid.element(grid_data=df_filtered)

    # Instead, we need to get a reference to the widget and call .update_grid_data in a use_effect
    def update_df():
        # NOTE: the cast is optional, and only needed if you like type hinting
        grid_widget = cast(ipyaggrid.Grid, solara.get_widget(grid))
        grid_widget.update_grid_data(df_filtered)

    # Note, instead of having df_filtered as a dependency, we use species which is easier/cheaper
    # to compare.
    solara.use_effect(update_df, [species.value])
```

[Or check out our more worked out example](https://solara.dev/examples/libraries/ipyaggrid).


## ipydatagrid

The problem with ipydatagrid is similar to aggrid, except here we need to use the `dataframe` argument for the
constructor, and the `.data` property for updating the dataframe.

```solara
from typing import Dict, List, cast
import ipydatagrid
import plotly.express as px
import solara


df = px.data.iris()
species = solara.reactive("setosa")


@solara.component
def Page():
    df_filtered = df.query(f"species == {species.value!r}")
    solara.Select("Filter species", value=species, values=["setosa", "versicolor", "virginica"])
    datagrid = ipydatagrid.DataGrid.element(dataframe=df, selection_mode="row")

    # we need to use .data instead (on the widget) to update the dataframe
    # similar to aggrid
    def update_df():
        # NOTE: the cast is optional, and only needed if you like type hinting
        datagrid_widget = cast(ipydatagrid.DataGrid, solara.get_widget(datagrid))
        # Updating the dataframe goes via the .data property
        datagrid_widget.data = df

    solara.use_effect(update_df, [species.value])
```

[Or check out our more worked out example](https://solara.dev/examples/libraries/ipydatagrid).


## Wrapper libraries

However, because we care about type safety, we generate wrapper components for some libraries. This enables type completion in VSCode, type checks with VSCode, and mypy.

The following libraries are fully wrapped:

  * `ipywidgets` wrapper: `reacton.ipywidgets`
  * `ipyvuetify` wrapper: `reacton.ipyvuetify`
  * `bqplot` wrapper: `reacton.bqplot`
  * `ipycanvas` wrapper: `reacton.ipycanvas`

This allows us to do instead:
```python
import reacton.ipywidgets as w
button_element = w.Button(description="Click me)
```

And enjoy auto complete and type checking.

## Create your own wrapper

The best example would be to take a look at the source code for now:

  * [ipywidgets](https://github.com/widgetti/reacton/blob/master/reacton/ipywidgets.py)
  * [bqplot](https://github.com/widgetti/reacton/blob/master/reacton/bqplot.py)
  * [ipyvuetify](https://github.com/widgetti/reacton/blob/master/reacton/ipyvuetify.py)

The code is generated by executing:

    $ python -m reacton.ipywidgets


## Limitation

Reacton assumes the widget constructor arguments match the traits. If this is not the case, this may result in runtime errors. If this leads to issues, please open an [Issue](https://github.com/widgetti/solara/issues/new) to discuss this.
