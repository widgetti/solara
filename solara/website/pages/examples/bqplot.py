import numpy as np
import reacton.bqplot as bqplot
import reacton.ipywidgets as w
import solara

x0 = np.linspace(0, 2, 100)


@solara.component
def Page(x=x0, ymax=5):
    with w.VBox() as main:
        y = x ** w.slider_float(1, min=0.1, max=3, description="Exponent")

        x_scale = bqplot.LinearScale()
        if w.checkbox(False, description="Log scale"):
            y_scale = bqplot.LogScale(min=0.1, max=ymax)
        else:
            y_scale = bqplot.LinearScale(min=0, max=ymax)

        display_legend = w.checkbox(True, "Show legend")
        label = ""
        if display_legend:
            label = w.text("My Label", "legend label")

        color = w.color("red", "Line color")

        lines = bqplot.Lines(x=x, y=y, scales={"x": x_scale, "y": y_scale}, stroke_width=3, colors=[color], display_legend=display_legend, labels=[label])
        x_axis = bqplot.Axis(scale=x_scale)
        y_axis = bqplot.Axis(scale=y_scale, orientation="vertical")
        bqplot.Figure(axes=[x_axis, y_axis], marks=[lines], scale_x=x_scale, scale_y=y_scale, layout={"min_width": "800px"})

    return main
