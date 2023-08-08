# ipyvuetify

 * [Documentation](https://ipyvuetify.readthedocs.io/)
 * [GitHub](https://github.com/widgetti/ipyvuetify)


ipyvuetify is an [ipywidget based](./ipywidgets) library, that wraps the [Vuetify component library](https://v2.vuetifyjs.com/) to give beautiful
material design based widgets.

![ipyvuetify screencast demo](https://user-images.githubusercontent.com/46192475/79730684-78954880-82f1-11ea-855b-43a2b619ca04.gif)

## Reacton and ipyvuetify

We consider ipyvuetify one of the most essential ipywidget libraries, and that is the reason why [Reacton](/docs/understanding/reacton) ships with
generated ipyvuetify components to make your app type safe.

```solara

import solara
# rv is the reacton-ipyvuetify wrapper for Reacton/Solara
import reacton.ipyvuetify as rv


@solara.component
def Page():
    clicks, set_clicks = solara.use_state(0)
    def my_click_handler(*ignore_args):
        # trigger a new render with a new value for clicks
        set_clicks(clicks+1)
    button = rv.Btn(children=[f"Clicked {clicks} times"])
    rv.use_event(button, 'click', my_click_handler)
    return button
```


## Solara and ipyvuetify

Many of the Solara components are based on ipyvuetify. Do not hesitate the look at the [source code of the Solara components](https://github.com/widgetti/solara/tree/master/solara/components) to learn how to create your own components.
