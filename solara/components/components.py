from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter
import pygments
from typing import List
import react_ipywidgets as react
import react_ipywidgets.ipywidgets as w
import react_ipywidgets.ipyvuetify as v
import solara.widgets

PivotTable = react.core.ComponentWidget(solara.widgets.PivotTable)
# GridLayoutRaw = react.core.ComponentWidget(solara.widgets.GridLayout)


def ui_dropdown(value="foo", options=["foo", "bar"], description="", key=None, **kwargs):
    key = key or str(value) + str(description) + str(options)
    value, set_value = react.use_state(value, key)

    def set_index(index):
        set_value(options[index])

    v.Select(v_model=value, label=description, items=options, on_v_model=set_value, clearable=True)
    return value

# def ui_checkbox(value="foo", options=["foo", "bar"], description="", key=None, **kwargs):
#     key = key or str(value) + str(description) + str(options)
#     value, set_value = react.use_state(value, key)

#     def set_index(index):
#         set_value(options[index])

#     v.Select(v_model=value, label=description, items=options, on_v_model=set_value, clearable=True)
#     return value


def ui_checkbox(value=True, description="", key=None, **kwargs):
    key = key or str(value) + str(description)
    value, set_value = react.use_state(value, key)
    v.Checkbox(v_model=value, label=description, on_v_model=set_value)
    return value


@react.component
def Image(data):
    def data_2_png(data, format="png"):
        import io
        import PIL.Image

        im = PIL.Image.fromarray(data[::], "RGB")
        f = io.BytesIO()
        im.save(f, format)
        return f.getvalue()

    value = data_2_png(data)
    return w.Image(value=value)


@react.component
def MarkdownIt(md_text: str, highlight: List[int] = []):
    # # from myst_parser.main import to_html

    # # html = to_html(md)
    # import markdown

    # # from ipywidgets import HTML

    # html = markdown.markdown(md, extensions=["codehilite"])
    # print(md, html)

    from markdown_it import MarkdownIt as MarkdownItMod
    from mdit_py_plugins.front_matter import front_matter_plugin
    from mdit_py_plugins.footnote import footnote_plugin
    from mdit_py_plugins import container, deflist

    def highlight_code(code, name, attrs):
        """Highlight a block of code"""
        hl_lines = highlight
        if attrs:
            print(f"Ignoring {attrs}")

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

    return w.HTML(value=html)


@react.component
def Markdown(md_text: str):
    import markdown

    html = markdown.markdown(md_text, extensions=["pymdownx.highlight", "pymdownx.superfences", "pymdownx.emoji"])
    return w.HTML(value=html)


@react.component
def Code(path, path_header=None):
    path_header = path_header or path
    with open(path) as f:
        code = f.read()
    md = Markdown(
        f"""
### {path_header}

```python
{code}
```

"""
    )

    with v.ExpansionPanels() as main:
        with v.ExpansionPanel():
            with v.ExpansionPanelHeader(children=["View source"]):
                pass
            with v.ExpansionPanelContent(children=[md]):
                pass
    return main
