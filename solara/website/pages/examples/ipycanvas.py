import ipycanvas
import numpy as np
import solara
from reacton import ipycanvas as c
from reacton import ipywidgets as w


def polygon(canvas, x, y, radius1, radius2, n_points):
    index = np.arange(n_points)
    angles = (2 * np.pi / n_points) * index

    radius = np.where(index % 2, radius1, radius2)
    v_x = x + np.cos(angles) * radius
    v_y = y + np.sin(angles) * radius

    points = np.stack((v_x, v_y), axis=1)

    canvas.fill_polygon(points)
    canvas.stroke_polygon(points)


@solara.component
def Page():
    width, height = 800, 800
    view_count, set_view_count = solara.use_state(0)
    with w.ViewcountVBox(set_view_count) as main:
        fill = w.color("#63934e", "fill color")
        stroke = w.color("#4e6393", "stroke color")
        line_width = w.slider_int(4, description="line width", min=0, max=30)
        n_points = w.slider_int(5, "Points", min=1, max=8) * 2
        radius_inner = w.slider_float(30, "Inner radius", min=0, max=100)
        radius_outer = w.slider_float(80, "Outer radius", min=0, max=100)

        def real_drawing():
            canvas: ipycanvas.Canvas = solara.core.get_widget(canvas_element)

            with ipycanvas.hold_canvas(canvas):
                canvas.clear()
                canvas.fill_style = fill
                canvas.stroke_style = stroke
                canvas.line_width = line_width
                radius = width // 3
                polygon(canvas, width // 2, height // 2, radius * radius_inner / 100, radius * radius_outer / 100, n_points)

        solara.use_side_effect(real_drawing, [fill, stroke, line_width, n_points, view_count, radius_inner, radius_outer])
        canvas_element = c.Canvas(width=width, height=height)

    return main
