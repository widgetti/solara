from typing import Callable

from bokeh.core.serialization import DeserializationError
from bokeh.io import curdoc
from bokeh.models import Plot
from bokeh.plotting import figure
from bokeh.themes import Theme
from jupyter_bokeh import BokehModel

import solara
from solara.components.component_vue import component_vue


class SafeBokehModel(BokehModel):
    """BokehModel with the upstream teardown faults patched out.

    Both bugs are in jupyter_bokeh 4.1.0 and are patched here rather than in a
    fork
    """

    def close(self) -> None:
        """Detaches document callbacks only while still registered.

        We have the explicit cleanup callback + solara cleans the widget, but
        ipywidgets calls close() again from gc (via __del__), which raises KeyError
        for an already deleted object
        """
        # skips the BokehModel.close and goes straight to the ipywidgets teardown
        super(BokehModel, self).close()
        document = self._document
        if document is not None:
            registry = getattr(document.callbacks, "_change_callbacks", {})
            if self in registry:  # only remove if we are in the registry
                document.remove_on_change(self)

    def _sync_model(self, model, content, buffers) -> None:
        """Drops frontend events that fail to deserialize.

        An event can reference a model already removed or replaced server side,
        which otherwise raises DeserializationError from ipywidgets
        """
        try:
            super()._sync_model(model, content, buffers)
        except DeserializationError:
            return


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
    # state variables
    loaded = solara.use_reactive(False)
    dark = solara.lab.use_dark_effective()
    BokehLoaded(loaded=loaded.value, on_loaded=loaded.set)

    fig_element = BokehModel.element(model=fig)  # main object

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

    def cleanup_widget():
        # explicitly adds a teardown cleanup callback for the widget on unmount
        # the comm and document callbacks are detached manually, rather than on garbage collection
        def cleanup():
            try:
                fig_widget: BokehModel = solara.get_widget(fig_element)
            except Exception:
                return
            if isinstance(fig_widget, BokehModel):
                # close() detaches the doc callbacks + shuts the comm
                fig_widget.close()

        return cleanup

    solara.use_effect(cleanup_widget, dependencies=[])

    def set_init_theme():
        # this might or might not do something
        curdoc().theme = dark_theme if dark else light_theme

    solara.use_memo(set_init_theme, dependencies=[])

    if loaded.value:
        return fig_element
