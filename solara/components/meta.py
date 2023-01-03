from typing import Optional

import solara

from .head_tag import HeadTag


@solara.component
def Meta(name: Optional[str] = None, property: Optional[str] = None, content: Optional[str] = None):
    """Add a meta tag to the head element, or replace a meta tag with the same name and or property.

    This component should be used inside a [Head](/api/head) component, e.g.:

    ```python
    import solara

    @solara.component
    def Page():
        with solara.VBox() as main:
            MyAwesomeComponent()
            with solara.Head():
                solara.Meta(name="description", property="og:description", content="My page description")
                solara.Meta(property="og:title", content="My page title for social media")
                solara.Meta(property="og:image", content="https://solara.dev/static/assets/images/logo.svg")
                solara.Meta(property="og:type", content="website")
        return main
    ```

    If multiple Meta components are used with the same name+description, the 'deepest' child will take precedence.

    ## Arguments

     * name: The name of the meta tag, used in standard meta tags
     * property: the property of the meta tag, used in Open Graph tags.
     * content: The content of the meta tag.
    """
    attributes = {}
    key = ""
    if name is not None:
        attributes["name"] = name
        key += "-" + name
    if property is not None:
        attributes["property"] = property
        key += "-" + property
    if content is not None:
        attributes["content"] = content
    return HeadTag(tagname="meta", attributes=attributes, key=key)
