"""
# ipyleaflet
Map visualization using [ipyleaflet](https://ipyleaflet.readthedocs.io/), a ipywidgets wrapper for [leaflet.js](https://leafletjs.com/)
"""
import ipyleaflet

import solara

zoom = solara.reactive(5)
center = solara.reactive((53.2305799, 6.5323552))


@solara.component
def Page():
    with solara.Column(style={"min-width": "500px", "height": "500px"}):
        # solara components support reactive variables
        solara.SliderInt(label="Zoom level", value=zoom, min=1, max=20)
        # using 3rd party widget library require wiring up the events manually
        # using zoom.value and zoom.set
        ipyleaflet.Map.element(  # type: ignore
            zoom=zoom.value,
            on_zoom=zoom.set,
            center=center.value,
            on_center=center.set,
            scroll_wheel_zoom=True,
        )
        solara.Text(f"Zoom: {zoom.value}")
        solara.Text(f"Center: {center.value}")
