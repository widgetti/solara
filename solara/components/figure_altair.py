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

    See also [our altair example](/examples/libraries/altair).

    ## Arguments

    - chart: Altair chart
    - on_click: Callback function for click events.
    - on_hover: Callback function for hover events.

    """
    import altair as alt

    with alt.renderers.enable("mimetype"):
        bundle = chart._repr_mimebundle_()[0]
        key4 = "application/vnd.vegalite.v4+json"
        key5 = "application/vnd.vegalite.v5+json"
        if key4 not in bundle and key5 not in bundle:
            raise KeyError(f"{key4} and {key5} not in mimebundle:\n\n{bundle}")
        spec = bundle.get(key5, bundle.get(key4))
        return solara.widgets.VegaLite.element(
            spec=spec, on_click=on_click, listen_to_click=on_click is not None, on_hover=on_hover, listen_to_hover=on_hover is not None
        )


# alias for backward compatibility
AltairChart = FigureAltair
