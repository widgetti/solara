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
        key4 = "application/vnd.vegalite.v4+json"
        key5 = "application/vnd.vegalite.v5+json"
        key6 = "application/vnd.vegalite.v6.json"
        if key6 in bundle:
            version = 6
            spec = bundle.get(key6)
        elif key5 in bundle:
            version = 5
            spec = bundle.get(key5)
        elif key4 in bundle:
            version = 4
            spec = bundle.get(key4)
        else:
            raise KeyError(f"{key4} and {key5} and {key6} not in mimebundle:\n\n{bundle}")

    return solara.widgets.VegaLite.element(
        version=version,
        spec=spec,
        on_click=on_click,
        listen_to_click=on_click is not None,
        on_hover=on_hover,
        listen_to_hover=on_hover is not None,
    )


# alias for backward compatibility
AltairChart = FigureAltair
