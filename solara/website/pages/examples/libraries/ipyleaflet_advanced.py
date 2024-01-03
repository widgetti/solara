"""
# ipyleaflet advanced

Extends the [basic ipyleaflet example](/examples/libraries/ipyleaflet) with a marker that can be dragged around, and a
dropdown to select the map style. Two buttons allow to reset the map to the default zoom and center and to zoom
to the marker.
"""
import ipyleaflet

import solara

center_default = (53.2305799, 6.5323552)
zoom_default = 5
maps = {
    "OpenStreetMap.Mapnik": ipyleaflet.basemaps.OpenStreetMap.Mapnik,
    "OpenTopoMap": ipyleaflet.basemaps.OpenTopoMap,
    "Esri.WorldTopoMap": ipyleaflet.basemaps.Esri.WorldTopoMap,
}

zoom = solara.reactive(zoom_default)
center = solara.reactive(center_default)
marker_location = solara.reactive(center_default)

map_name = solara.reactive(list(maps)[0])


@solara.component
def Page():
    def location_changed(location):
        # do things with the location
        marker_location.set(location)

    with solara.Column(style={"min-width": "500px", "height": "500px"}):
        solara.Markdown(f"Market set to: {marker_location.value}", style={"color": "#6e6e6e"})

        map = maps[map_name.value]
        url = map.build_url()

        def goto_marker():
            center.value = marker_location.value
            zoom.value = 13

        def reset_view():
            center.value = center_default
            zoom.value = zoom_default

        solara.Select(label="Map", value=map_name, values=list(maps))
        solara.SliderInt(label="Zoom level", value=zoom, min=1, max=20)
        with solara.Row():
            solara.Button(label="Zoom to marker", on_click=goto_marker)
            solara.Button(label="Reset view", on_click=reset_view)

        # Isolation is required to prevent the map from overlapping navigation (when screen width < 960px)
        with solara.Column(style={"isolation": "isolate"}):
            ipyleaflet.Map.element(  # type: ignore
                zoom=zoom.value,
                on_zoom=zoom.set,
                center=center.value,
                on_center=center.set,
                scroll_wheel_zoom=True,
                layers=[
                    ipyleaflet.TileLayer.element(url=url),
                    ipyleaflet.Marker.element(location=marker_location.value, draggable=True, on_location=location_changed),
                ],
            )
