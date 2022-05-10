"""
Renders markdown using https://python-markdown.github.io/
"""


from solara.kitchensink import react, sol, w


@react.component
def MarkdownDemo():
    markdown_initial = """
# Large
## Smaller

```python
code = "formatted" and "supports highlighting"
```

    * item 1
    * item 2

    """.strip()
    markdown_text, set_markdown_text = react.use_state(markdown_initial)
    # with sol.HBox() as main:
    with sol.GridFixed(columns=2) as main:
        sol.Markdown("Input text")
        sol.Markdown("Renders like")
        w.Textarea(value=markdown_text, on_value=set_markdown_text, layout={"min_height": "400px"})
        # v.Textarea(v_model=markdown_text, on_v_model=set_markdown_text, height="400px", style_="border: 1px solid black;")
        sol.Markdown(markdown_text)

    return main


Component = sol.Markdown
App = MarkdownDemo
