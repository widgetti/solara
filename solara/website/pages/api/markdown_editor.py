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
# Large heading
## Medium heading
### Small heading


## List items

   * item 1
   * item 2

## Numbered items

   1. item 1
   2. item 2


**bold** and *italic*, [GitHub link](https://github.com/widgetti/solara/)


```
preformatted code
which respecs spaces
and line breaks
```

    """.strip()

    markdown_text, set_markdown_text = solara.use_state(markdown_initial)
    with solara.HBox(grow=True) as main:
        with solara.VBox():
            with solara.Padding(2):
                with rv.Sheet(elevation=2):
                    solara.MarkdownEditor(markdown_text, on_value=set_markdown_text)
                with rv.Sheet(elevation=2):
                    solara.Markdown("# Raw markdown")
                    solara.Preformatted(markdown_text)

    return main
