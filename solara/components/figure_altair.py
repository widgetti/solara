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

    if "application/vnd.vegalite.v4+json" in bundle:
        spec = bundle["application/vnd.vegalite.v4+json"]

    elif "application/vnd.vegalite.v5+json" in bundle:
        spec = bundle["application/vnd.vegalite.v5+json"]

    else:
        # Altair 6+ emits newer Vega-Lite MIME types (e.g. v6).
        # Fall back to the first Vega-Lite spec we find instead of failing hard.

        

        for key in bundle:
            if key.startswith("application/vnd.vegalite.v"):
                spec = bundle[key]
                break
        else:
            raise KeyError(
                f"Unsupported Vega-Lite MIME type: {list(bundle.keys())}"
            )

    
        return solara.widgets.VegaLite.element(
            spec=spec, on_click=on_click, listen_to_click=on_click is not None, on_hover=on_hover, listen_to_hover=on_hover is not None
        )


# alias for backward compatibility
AltairChart = FigureAltair
