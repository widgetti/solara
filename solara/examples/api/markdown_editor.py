"""
Renders markdown using https://python-markdown.github.io/

Code marked with language "solara" will be executed only when the argument `unsafe_solara_execute=False` is passed.

This argument is marked "unsafe" to make users aware it can be used to execute arbitrary code.
If the markdown is fixed (such as in our own documentation) this should not pose any security risk.

"""


from solara.kitchensink import react, sol, v


@react.component
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

    markdown_text, set_markdown_text = react.use_state(markdown_initial)
    with sol.HBox(grow=True) as main:
        with sol.VBox():
            with sol.Padding(2):
                with v.Sheet(elevation=2):
                    sol.MarkdownEditor(markdown_text, on_value=set_markdown_text)
                with v.Sheet(elevation=2):
                    sol.Markdown("# Raw markdown")
                    sol.Preformatted(markdown_text)

    return main
