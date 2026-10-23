import solara
from solara.alias import rv

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

    """.strip()


@solara.component
def MarkdownEditor():
    markdown_text, set_markdown_text = solara.use_state(markdown_initial)
    with solara.ColumnsResponsive(12, medium=6):
        with solara.Column():
            solara.Markdown("# Input text")
            with solara.Padding(2):
                with rv.Sheet(elevation=2):
                    rv.Textarea(v_model=markdown_text, on_v_model=set_markdown_text, rows=20)
        with solara.Column():
            solara.Markdown("# Renders like")
            with solara.Padding(2):
                solara.Markdown(markdown_text)
        with solara.Sidebar():
            with solara.Row():
                solara.Button("Clear", on_click=lambda: set_markdown_text(""))
                solara.Button("Reset ", on_click=lambda: set_markdown_text(markdown_initial))


# create an alias of the Markdown Editor component so Solara can find it
Page = MarkdownEditor
