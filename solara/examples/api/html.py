"""
# HTML

Insert a custom html tag, possible with unescaped html text inside.

Note that this will be interpreted by the browser, so make sure the input html text
cannot include code from users.
"""

from solara.kitchensink import react, sol


@react.component
def HTMLDemo():
    html = """
<h1>Custom html</h1>
<ul>
    <li>Item 1
    <li>Item 2
</ul>
"""
    with sol.VBox() as main:
        sol.HTML(tag="div", unsafe_innerHTML=html)
    return main


Component = sol.HTML
App = HTMLDemo
