from typing import Callable

import solara
from solara.components.component_vue import component_vue
from bokeh.io import output_notebook
from bokeh.models import Plot
from bokeh.plotting import figure
from bokeh.themes import Theme
from jupyter_bokeh import BokehModel


@component_vue("bokehloaded.vue")
def BokehLoaded(loaded: bool, on_loaded: Callable[[bool], None]):
    pass


@solara.component
def FigureBokeh(
    fig,
    dependencies=None,
    light_theme: str | Theme = "light_minimal",
    dark_theme: str | Theme = "dark_minimal",
):
    """
    Display a Bokeh figure or Plot.

    ## Example

    ```solara
    import solara
    import solara.lab
    from bokeh.plotting import figure

    @solara.component
    def Page():
        p = figure(width=600, height=400)
        p.line(x=[1, 2, 3, 4, 5], y=[2, 4, 2, 7, 9])

        return solara.lab.FigureBokeh(p)
    ```

    For performance reasons, you might want to pass in a list of dependencies that indicate when
    the figure changed, to avoid re-rendering it on every render.

    ## Arguments

    * fig: `Plot` or `figure` object to display.
    * dependencies: List of dependencies to watch for changes, if None, will rerender when `fig` is changed.
    * light_theme: The name or `bokeh.themes.Theme` object to use for light mode. Defaults to `"light_minimal"`.
    * dark_theme: The name or `bokeh.themes.Theme` object to use for dark mode. Defaults to `"dark_minimal"`.
    """
    loaded = solara.use_reactive(False)
    dark = solara.lab.use_dark_effective()
    output_notebook(hide_banner=True)
    BokehLoaded(loaded=loaded.value, on_loaded=loaded.set)

    # TODO: there's an error with deletion on the doc. do we need to modify the underlying class?
    fig_element = BokehModel.element(model=fig)

    def update_data():
        fig_widget: BokehModel = solara.get_widget(fig_element)
        fig_model: Plot | figure = fig_widget._model  # base class for figure
        if fig != fig_model:  # don't run through on first startup
            # pause until all updates complete
            with fig_model.hold(render=True):
                # extend renderer set and cull previous
                length = len(fig_model.renderers)
                fig_model.renderers.extend(fig.renderers)
                fig_model.renderers = fig_model.renderers[length:]

                # similarly update plot layout properties
                places = ["above", "below", "center", "left", "right"]
                for place in places:
                    attr = getattr(fig_model, place)
                    newattr = getattr(fig, place)
                    length = len(attr)
                    attr.extend(newattr)
                    setattr(fig_model, place, attr[length:])

    def update_theme():
        # NOTE: using bokeh.io.curdoc and this _document prop will point to the same object
        fig_widget: BokehModel = solara.get_widget(fig_element)
        if dark:
            fig_widget._document.theme = dark_theme
        else:
            fig_widget._document.theme = light_theme

    solara.use_effect(update_data, dependencies or fig)
    solara.use_effect(update_theme, [dark, loaded.value])

    if loaded.value:
        return fig_element
    else:
        # NOTE: the returned object will be a v.Sheet until Bokeh is loaded
        # BUG: this will show the JS error temporarily before loading
        with solara.Card(margin=0, elevation=0):
            with solara.Row(justify="center"):
                solara.SpinnerSolara(size="200px")
