import ipyvue
import traitlets

import solara


class SpinnerSolaraWidget(ipyvue.VueTemplate):
    template_file = (__file__, "spinner-solara.vue")

    size = traitlets.Unicode("64px").tag(sync=True)


@solara.component
def SpinnerSolara(size="64px"):
    """Spinner component with the Solara logo to indicate the app is busy.

    ### Basic example

    ```solara
    import solara

    @solara.component
    def Page():
        solara.SpinnerSolara(size="100px")
    ```

    ## Arguments
     * `size`: Size of the spinner.
    """
    return SpinnerSolaraWidget.element(size=size)
