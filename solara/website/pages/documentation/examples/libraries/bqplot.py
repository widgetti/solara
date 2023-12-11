"""
# bqplot

[bqplot](https://github.com/bqplot/bqplot) is a 2-D visualization system for Jupyter, based on the constructs of the Grammar of Graphics.
"""

import numpy as np
import reacton.bqplot as bqplot

import solara

x0 = np.linspace(0, 2, 100)

exponent = solara.reactive(1.0)
log_scale = solara.reactive(False)


@solara.component
def Page(x=x0, ymax=5):
    y = x**exponent.value
    color = "red"
    display_legend = True
    label = "bqplot graph"

    solara.SliderFloat(value=exponent, min=0.1, max=3, label="Exponent")
    solara.Checkbox(value=log_scale, label="Log scale")

    x_scale = bqplot.LinearScale()
    if log_scale.value:
        y_scale = bqplot.LogScale(min=0.1, max=ymax)
    else:
        y_scale = bqplot.LinearScale(min=0, max=ymax)

    lines = bqplot.Lines(x=x, y=y, scales={"x": x_scale, "y": y_scale}, stroke_width=3, colors=[color], display_legend=display_legend, labels=[label])
    x_axis = bqplot.Axis(scale=x_scale)
    y_axis = bqplot.Axis(scale=y_scale, orientation="vertical")
    bqplot.Figure(axes=[x_axis, y_axis], marks=[lines], scale_x=x_scale, scale_y=y_scale, layout={"min_width": "800px"})

    # return main
