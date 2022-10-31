import ipyvuetify as vy
import reacton.core
import traitlets

import solara


class TitleWidget(vy.VuetifyTemplate):
    template_file = (__file__, "title.vue")
    title = traitlets.Unicode().tag(sync=True)
    level = traitlets.Int().tag(sync=True)


@solara.component
def Title(title: str):
    """Set the title of a page.

    This component should be used inside a [Head](/api/head) component, e.g.:

    ```python
    import solara

    @solara.component
    def Page():
        with solara.VBox() as main:
            MyAwesomeComponent()
            with solara.Head():
                solara.Title("My page title")
        return main
    ```

    If multiple Title components are used, the 'deepest' child will take precedence.

    ## Arguments

     * title: the title of the page
    """
    level = 0
    rc = reacton.core.get_render_context()
    context = rc.context
    while context and context.parent:
        level += 1
        context = context.parent
    return TitleWidget.element(title=title, level=level)
