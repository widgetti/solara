"""

# Component.widget

Create a classic ipywidget from a component.

```python
def widget(self, **kwargs):
    ...
```


This will create a widget from the component. The widget will be a
subclass of `ipywidgets.VBox` and `ipywidgets.ValueWidget`.

Example

```python
import solara
widget = solara.FileDownload.widget(data="some text data", filename="solara-demo.txt")
```

This is very useful if you are migrating your application from a classic
ipywidget to solara. See [also the ipywidgets tutorial](/docs/tutorial/ipywidgets).

The `ipywidgets.ValueWidget` is used to enable the use of the widget in
interact, or interactive. The `ipywidgets.VBox` is used to enable
nesting of widgets.

All keyword arguments will be passed to the component.
Each argument pair of `on_<name>` and `<name>` will
be added as a trait in the widget.

For example,

```solara
import solara
import ipywidgets as widgets
import random


countries_demo_data = {
    "Netherlands": ["Amsterdam", "Rotterdam", "The Hague"],
    "Germany": ["Berlin", "Hamburg", "Munich"],
    "France": ["Paris", "Marseille", "Lyon"],
}


# this component can be used in a component three, but ...
@solara.component
def LocationSelect(value, on_value, countries=countries_demo_data):
    country, city = value
    cities = countries.get(country, [])
    # reset to None if not in the list of countries
    if city not in cities:
        city = None
        # update the state if we changed/reset city
        on_value((country, city))

    with solara.Card("Location"):
        solara.Select(label="country",
                      values=list(countries),
                      value=country,
                      on_value=lambda country: on_value((country, city)),
        )
        solara.Select(label="city",
                      values=cities,
                      value=city,
                      on_value=lambda city: on_value((country, city)),
        )


# Using .widget(...) we can create a widget from it.
# For use with interact:
@widgets.interact(location=LocationSelect.widget(value=("Netherlands", "Amsterdam")))
def f(size=3.4, location=None):
    print(size, location)


# Or to add to your VBox:
widgets.VBox(
    [LocationSelect.widget(value=("Netherlands", "Amsterdam"))]
)

# this is how you'd use it as a component
@solara.component
def Page():
    value, set_value = solara.use_state(("Netherlands", "Amsterdam"))
    def pick():
        country = random.choice(list(countries_demo_data))
        city = random.choice(countries_demo_data[country])
        set_value((country, city))

    LocationSelect(value=value, on_value=set_value)
    solara.Button("Pick random place", on_click=pick)

```

"""

from . import NoPage

Page = NoPage
title = "widget"
