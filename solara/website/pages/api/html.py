"""
# HTML

Insert a custom html tag, possible with unescaped html text inside.

Note that this will be interpreted by the browser, so make sure the input html text
cannot include code from users.
"""

import solara


@solara.component
def Page():
    html = """
<h1>Custom html</h1>
<ul>
    <li>Item 1
    <li>Item 2
</ul>
"""
    with solara.VBox() as main:
        solara.HTML(tag="div", unsafe_innerHTML=html)
    return main
