from typing import Callable

import ipyvuetify
import traitlets

import solara


class EchartsWidget(ipyvuetify.VuetifyTemplate):
    template_file = (__file__, "echarts.vue")

    attributes = traitlets.Dict(default_value=None, allow_none=True).tag(sync=True)

    maps = traitlets.Any({}).tag(sync=True)
    option = traitlets.Any({}).tag(sync=True)
    on_click = traitlets.Callable(None, allow_none=True)

    def vue_on_click(self, data):
        if self.on_click:
            self.on_click(data)


@solara.component
def FigureEcharts(option: dict = {}, on_click: Callable = None, maps: dict = {}, attributes={"style": "height: 400px"}):
    """Create a Echarts figure.

    See [The Echarts website for examples](https://echarts.apache.org/)

    Note that we do not support a Python API to create the figure data.

    A library such as Pyecharts can help you with that, otherwise you can provide
    the data simply as data similarly as on the Echarts example webpage.

    # Arguments

    * option: dict, the option for the figure, see the echart documentation.
    * on_click: Callable, a function that will be called when the user clicks on the figure.
    * maps: dict, a dictionary of maps to be used in the figure.
    * attributes: dict, a dictionary of attributes to be passed to the container (like style, class).


    """
    return EchartsWidget.element(option=option, on_click=on_click, maps=maps, attributes=attributes)
