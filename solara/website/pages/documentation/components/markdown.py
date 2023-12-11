"""# Markdown
"""


import solara
from solara.alias import rv
from solara.website.utils import apidoc


@solara.component
def Page():
    markdown_initial = """
# Large
## Smaller

## List items

    * item 1
    * item 2


## Code highlight support
```python
code = "formatted" and "supports highlighting"
```


## Mermaid support!
See [Mermaid docs](https://mermaid-js.github.io/)

```mermaid
graph TD;
    A-->B;
    A-->C;
    B-->D;
    C-->D;
```


    """.strip()

    markdown_text, set_markdown_text = solara.use_state(markdown_initial)
    # with solara.GridFixed(columns=2) as main:
    with solara.HBox(grow=True) as main:
        with solara.VBox():
            solara.Markdown("# Input text")
            with solara.Padding(2):
                with rv.Sheet(elevation=2):
                    rv.Textarea(v_model=markdown_text, on_v_model=set_markdown_text, rows=30)
        with solara.VBox():
            solara.Markdown("# Renders like")
            with solara.Padding(2):
                with rv.Sheet(elevation=2):
                    solara.Markdown(markdown_text)

    return main


__doc__ += apidoc(solara.Markdown.f)  # type: ignore
