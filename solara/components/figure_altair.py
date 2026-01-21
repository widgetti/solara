from typing import Any, Callable

import solara
import solara.widgets


@solara.component
def FigureAltair(
    chart,
    on_click: Callable[[Any], None] = None,
    on_hover: Callable[[Any], None] = None,
):
    """Renders an Altair chart using VegaLite.

    See also [our altair example](/documentation/examples/libraries/altair).

    ## Arguments

    - chart: Altair chart
    - on_click: Callback function for click events.
    - on_hover: Callback function for hover events.

    """
    import altair as alt

    with alt.renderers.enable("mimetype"):
        bundle = chart._repr_mimebundle_()[0]
        # Find the Vega-Lite spec from the bundle (supports v4, v5, v6+)
        # MIME type format varies: v4/v5 use "+json" suffix, v6 uses ".json"
        spec = None
        for key in bundle:
            if key.startswith("application/vnd.vegalite.v"):
                spec = bundle[key]
                break
        if spec is None:
            raise KeyError(f"No Vega-Lite MIME type found in mimebundle: {list(bundle.keys())}")
        return solara.widgets.VegaLite.element(
            spec=spec, on_click=on_click, listen_to_click=on_click is not None, on_hover=on_hover, listen_to_hover=on_hover is not None
        )


# alias for backward compatibility
AltairChart = FigureAltair
