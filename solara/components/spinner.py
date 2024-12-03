import ipyvue
import traitlets

import solara


class SpinnerSolaraWidget(ipyvue.VueTemplate):
    template_file = (__file__, "spinner-solara.vue")

    size = traitlets.Unicode("64px").tag(sync=True)
    color_back = traitlets.Unicode("#FFCF64").tag(sync=True)
    color_front = traitlets.Unicode("#FF8C3E").tag(sync=True)


@solara.component
def SpinnerSolara(size="64px", color_back="#FFCF64", color_front="#FF8C3E"):
    """Spinner component with the Solara logo to indicate the app is busy.

    ## Examples
    ### Basic example

    ```solara
    import solara

    @solara.component
    def Page():
        solara.SpinnerSolara(size="100px")
    ```

    ## Changing the colors
    ```solara
    import solara

    @solara.component
    def Page():
        solara.SpinnerSolara(size="100px", color_back="Grey", color_front="Lime")
    ```


    ## Arguments
     * `size`: Size of the spinner.
     * `color_back`: Color of the spinner in the background.
     * `color_front`: Color of the spinner in the foreground.
    """
    return SpinnerSolaraWidget.element(size=size, color_back=color_back, color_front=color_front)
