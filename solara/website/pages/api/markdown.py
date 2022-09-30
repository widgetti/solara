"""
Renders markdown using https://python-markdown.github.io/

Code marked with language "solara" will be executed only when the argument `unsafe_solara_execute=False` is passed.

This argument is marked "unsafe" to make users aware it can be used to execute arbitrary code.
If the markdown is fixed (such as in our own documentation) this should not pose any security risk.

"""


import solara
from solara.alias import rv


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
