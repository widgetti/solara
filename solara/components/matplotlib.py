import io
from typing import Any, List

import solara
from solara.alias import rw


@solara.component
def FigureMatplotlib(
    figure,
    dependencies: List[Any] = None,
    format: str = "svg",
    **kwargs,
):
    """Display a matplotlib figure.


    ## Example

    ```solara
    import solara
    from matplotlib.figure import Figure

    @solara.component
    def Page():
        fig = Figure()
        ax = fig.subplots()
        ax.plot([1, 2, 3], [1, 4, 9])
        return solara.FigureMatplotlib(fig)
    ```

    When running under solara-server, we by default configure the same 'inline' backend as in the Jupyter notebook.

    For performance reasons, you might want to pass in a list of dependencies that indicate when
    the figure changed, to avoid re-rendering it on every render.

    ## Example using pyplot

    Note that it is also possible to use the pyplot interface, but be sure to close the figure not to leak memory.

    ```solara
    import solara
    import matplotlib.pyplot as plt

    @solara.component
    def Page():
        plt.figure()
        plt.plot([1, 2, 3], [1, 4, 9])
        plt.show()
        plt.close()
    ```

    Note that the figure is not the same size using the pyplot interface, due to the default figure size being different.


    ## Arguments

     * `figure`: Matplotlib figure.
     * `dependencies`: List of dependencies to watch for changes, if None, will convert the figure to a static image on each render.
     * `format`: The image format to to convert the Matplotlib figure to (png, jpg, svg, etc.)
     * `kwargs`: Additional arguments to passed to figure.savefig
    """

    def make_image():
        f = io.BytesIO()
        figure.savefig(f, format=format, **kwargs)
        return f.getvalue()

    value = solara.use_memo(make_image, dependencies)
    # mime type name is different from format name of matplotlib
    format_mime = format
    if format_mime == "svg":
        format_mime = "svg+xml"
    return rw.Image(value=value, format=format_mime)
