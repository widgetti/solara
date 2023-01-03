from typing import Optional

import ipyvuetify as vy
import reacton.core
import traitlets

import solara


class HeadTagWidget(vy.VuetifyTemplate):
    template_file = (__file__, "head_tag.vue")
    tagname = traitlets.Unicode().tag(sync=True)
    key = traitlets.Unicode(None, allow_none=True).tag(sync=True)
    attributes = traitlets.Dict().tag(sync=True)
    level = traitlets.Int().tag(sync=True)


@solara.component
def HeadTag(tagname: str, key=None, attributes: Optional[dict] = None):
    """Add a child element to head element, or replace a meta tag with the same tagname and key.

    This component should be used inside a [Head](/api/head) component, e.g.:

    ```python
    import solara

    @solara.component
    def Page():
        with solara.VBox() as main:
            MyAwesomeComponent()
            with solara.Head():
                solara.HeadTag(tagname="meta", attributes={"name": "description", "content": "My page description"})
        return main
    ```

    If multiple HeadTag components are used with the same key, the 'deepest' child will take precedence.

    ## Arguments

     * tagname: the tagname of the element (e.g. 'meta', 'link', 'script')
     * attributes: a dictionary of attributes to set on the element.
    """
    level = 0
    rc = reacton.core.get_render_context()
    context = rc.context
    while context and context.parent:
        level += 1
        context = context.parent
    attributes = attributes or {}
    return HeadTagWidget.element(tagname=tagname, key=key, attributes=attributes, level=level)
