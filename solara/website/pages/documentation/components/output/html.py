"""# HTML"""

import solara
from solara.website.utils import apidoc


@solara.component
def Page():
    html = """
<h1>Custom html</h1>
<ul>
    <li>Item 1
    <li>Item 2
</ul>
"""
    solara.HTML(tag="div", unsafe_innerHTML=html)


__doc__ += apidoc(solara.HTML.f)  # type: ignore
