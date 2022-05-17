import textwrap
from typing import List

import pygments
import pymdownx.superfences
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name

from solara.kitchensink import react, sol


@react.component
def MarkdownIt(md_text: str, highlight: List[int] = []):
    # # from myst_parser.main import to_html

    # # html = to_html(md)
    # import markdown

    # # from ipywidgets import HTML

    # html = markdown.markdown(md, extensions=["codehilite"])
    # print(md, html)
    md_text = textwrap.dedent(md_text)

    from markdown_it import MarkdownIt as MarkdownItMod
    from mdit_py_plugins import container, deflist  # noqa: F401
    from mdit_py_plugins.footnote import footnote_plugin  # noqa: F401
    from mdit_py_plugins.front_matter import front_matter_plugin  # noqa: F401

    def highlight_code(code, name, attrs):
        """Highlight a block of code"""
        hl_lines = highlight
        if attrs:
            print(f"Ignoring {attrs}")

        if name:
            lexer = get_lexer_by_name(name)
            formatter = HtmlFormatter(hl_lines=hl_lines)  # linenos=True)
            return pygments.highlight(code, lexer, formatter)

    md = MarkdownItMod(
        "js-default",
        {
            # "linkify": True,
            "html": True,
            "typographer": True,
            "highlight": highlight_code,
        },
    )
    # tokens = md.parse(md)
    md = md.use(container.container_plugin, name="note")
    html = md.render(md_text)
    # print(html)

    return sol.HTML(unsafe_innerHTML=html)


extension_configs = {
    "pymdownx.superfences": {
        "custom_fences": [
            {
                "name": "mermaid",
                "class": "mermaid",
                "format": pymdownx.superfences.fence_div_format,
            },
        ],
    }
}


@react.component
def Markdown(md_text: str):
    import markdown

    md_text = textwrap.dedent(md_text)

    html = markdown.markdown(
        md_text,
        extensions=[
            "pymdownx.highlight",
            "pymdownx.superfences",
            "pymdownx.emoji",
            "toc",  # so we get anchors for h1 h2 etc
        ],
        extension_configs=extension_configs,
    )
    return sol.HTML(unsafe_innerHTML=html, class_="solara-markdown", style="max-width: 1024px;")
