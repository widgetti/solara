from typing import Callable, Dict, Optional, Tuple, cast

import ipyvuetify as vy
import reacton.core
import traitlets

import solara
import solara.lab


class TitleWidget(vy.VuetifyTemplate):
    template_file = (__file__, "title.vue")
    title = traitlets.Unicode().tag(sync=True)
    level = traitlets.Int().tag(sync=True)


Titles = Dict[str, Tuple[int, str]]


def _set_titles_default(updater: Callable[[Titles], Titles]):
    pass


titles_context = solara.create_context(_set_titles_default)


def use_title_get() -> Optional[str]:
    titles, set_titles = solara.use_state(cast(Titles, {}))
    titles_context.provide(set_titles)  # type: ignore
    if titles:
        title = max([(order, title) for (key, (order, title)) in titles.items()], key=lambda x: x[0])[1]
    else:
        title = None
    return title


def use_title_set(title: str, offset: int):
    key = solara.use_unique_key(prefix="title-")
    set_titles = solara.use_context(titles_context)

    def update():
        set_titles(lambda titles: {**titles, key: (offset, title)})

    solara.use_effect(update, [title])

    def restore():
        def cleanup():
            def without(titles):
                titles_restored = titles.copy()
                titles_restored.pop(key, None)
                return titles_restored

            set_titles(without)

        return cleanup

    solara.use_effect(restore, [])


@solara.component
def Title(title: str):
    """Set the title of a page.

    ```python
    import solara

    @solara.component
    def Page():
        with solara.VBox() as main:
            MyAwesomeComponent()
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
    offset = 2**level
    use_title_set(title, offset)

    return TitleWidget.element(title=title, level=level)
