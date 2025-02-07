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


def FigureBokeh(
    fig,
    dependencies=None,
    light_theme: str | Theme = "light_minimal",
    dark_theme: str | Theme = "dark_minimal",
):
    # NOTE: no docstring because not a component.
    loaded = solara.use_reactive(False)
    dark = solara.lab.use_dark_effective()
    fig_key = solara.use_uuid4([])
    output_notebook(hide_banner=True)
    BokehLoaded(loaded=loaded.value, on_loaded=loaded.set)
    if loaded.value:
        # TODO: there's an error with deletion on the doc. do we need to modify the underlying class?
        fig_element = BokehModel.element(model=fig).key(fig_key)

        def update_data():
            fig_widget: BokehModel = solara.get_widget(fig_element)
            fig_model: Plot | figure = fig_widget._model  # base class for figure
            if fig != fig_model:  # don't run through on first startup
                # pause until all updates complete
                fig_model.hold_render = True

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
                    if place == "right":
                        fig_model.hold_render = False
                    setattr(fig_model, place, attr[length:])
            return

        def update_theme():
            # NOTE: using bokeh.io.curdoc and this _document prop will point to the same object
            fig_widget: BokehModel = solara.get_widget(fig_element)
            if dark:
                fig_widget._document.theme = dark_theme
            else:
                fig_widget._document.theme = light_theme

        solara.use_effect(update_data, dependencies or fig)
        solara.use_effect(update_theme, [dark, loaded.value])
        return fig_element
    else:
        # NOTE: we don't return this as to not break effect callbacks outside this function
        with solara.Card(margin=0, elevation=0):
            # the card expands to fit space
            with solara.Row(justify="center"):
                solara.SpinnerSolara(size="200px")
