from typing import Any, Callable

import ipyvuetify
import traitlets

import solara


class EchartsWidget(ipyvuetify.VuetifyTemplate):
    template_file = (__file__, "echarts.vue")

    attributes = traitlets.Dict(default_value=None, allow_none=True).tag(sync=True)

    maps = traitlets.Any({}).tag(sync=True)
    option = traitlets.Any({}).tag(sync=True)
    on_click = traitlets.Callable(None, allow_none=True)
    on_mouseover = traitlets.Callable(None, allow_none=True)
    # for performance, so we don't get events from the frontend we don't care about
    on_mouseover_enabled = traitlets.Bool(False).tag(sync=True)
    on_mouseout = traitlets.Callable(None, allow_none=True)
    # same, for performance
    on_mouseout_enabled = traitlets.Bool(False).tag(sync=True)

    def vue_on_click(self, data):
        if self.on_click:
            self.on_click(data)

    def vue_on_mouseover(self, data):
        if self.on_mouseover:
            self.on_mouseover(data)

    def vue_on_mouseout(self, data):
        if self.on_mouseout:
            self.on_mouseout(data)


@solara.component
def FigureEcharts(
    option: dict = {},
    on_click: Callable[[Any], Any] = None,
    on_mouseover: Callable[[Any], Any] = None,
    on_mouseout: Callable[[Any], Any] = None,
    maps: dict = {},
    attributes={"style": "height: 400px"},
):
    """Create a Echarts figure.

    See [The Echarts website for examples](https://echarts.apache.org/)

    Note that we do not support a Python API to create the figure data.

    A library such as Pyecharts can help you with that, otherwise you can provide
    the data simply as data similarly as on the Echarts example webpage.

    # Arguments

    * option: dict, the option for the figure, see the echart documentation.
    * on_click: Callable, a function that will be called when the user clicks on the figure.
    * on_mouseover: Callable, a function that will be called when the user moves the mouse over a certain component.
    * on_mouseout: Callable, a function that will be called when the user moves the mouse out of a certain component.
    * maps: dict, a dictionary of maps to be used in the figure.
    * attributes: dict, a dictionary of attributes to be passed to the container (like style, class).


    """
    return EchartsWidget.element(
        option=option,
        on_click=on_click,
        on_mouseover=on_mouseover,
        on_mouseover_enabled=on_mouseover is not None,
        maps=maps,
        on_mouseout=on_mouseout,
        on_mouseout_enabled=on_mouseout is not None,
        attributes=attributes,
    )
