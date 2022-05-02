from typing import Callable, List

import ipyvue as vue
import pygments
import react_ipywidgets as react
import react_ipywidgets.ipyvuetify as v
import react_ipywidgets.ipyvuetify as ipyvue
import react_ipywidgets.ipywidgets as w
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name

import solara.widgets

PivotTable = react.core.ComponentWidget(solara.widgets.PivotTable)
Navigator = react.core.ComponentWidget(solara.widgets.Navigator)
GridDraggable = react.core.ComponentWidget(solara.widgets.GridLayout)
# keep the old name for a while
GridLayout = GridDraggable


@react.component
def ListItem(title, icon_name: str = None, children=[]):
    if children:
        with v.ListItem(value=title) as main:
            v.ListItemTitle(children=[title])
            with v.ListItemIcon():
                v.Icon(children=[icon_name or ""])
        return v.ListGroup(children=children, v_slots=[{"name": "activator", "children": main}], sub_group=True, value=True, append_icon=icon_name)
    else:
        with v.ListItem(value=title) as main:
            with v.ListItemIcon():
                v.Icon(children=[icon_name or ""])
            v.ListItemTitle(children=[title])
        return main


def ui_dropdown(value="foo", options=["foo", "bar"], description="", key=None, disabled=False, **kwargs):
    key = key or str(value) + str(description) + str(options)
    value, set_value = react.use_state(value, key)

    def set_index(index):
        set_value(options[index])

    v.Select(v_model=value, label=description, items=options, on_v_model=set_value, clearable=True, disabled=disabled, **kwargs)
    return value


def ui_text(value="", description="Enter text", key=None, clearable=False, hint="", disabled=False, **kwargs):
    key = key or str(value) + str(description) + str(hint)
    value, set_value = react.use_state(value, key)
    v.TextField(v_model=value, label=description, on_v_model=set_value, clearable=clearable, hint=hint, disabled=disabled, **kwargs)
    return value


def ui_checkbox(value=True, description="", key=None, disabled=False, **kwargs):
    key = key or str(value) + str(description)
    value, set_value = react.use_state(value, key)
    v.Checkbox(v_model=value, label=description, on_v_model=set_value, **kwargs)
    return value


def ui_slider(value=1, description="", min=0, max=100, key=None, tick_labels=None, thumb_label=None, disabled=False, **kwargs):
    key = key or str(value) + str(description)
    value, set_value = react.use_state(value, key)
    v.Slider(
        v_model=value,
        label=description,
        min=min,
        max=max,
        on_v_model=set_value,
        ticks=tick_labels is not None,
        tick_labels=tick_labels,
        thumb_label=thumb_label,
        disabled=disabled,
        **kwargs,
    )
    return value


@react.component
def Text(text):
    return vue.Html.element(tag="span", children=[text])


@react.component
def Div(children=[], **kwargs):
    return vue.Html.element(tag="div", children=children, **kwargs)


@react.component
def Warning(text, icon="mdi-alert", children=[], **kwargs):
    return v.Alert(type="warning", text=True, prominent=True, icon=icon, children=[text, *children], **kwargs)


@react.component
def Info(text, icon="mdi-alert", children=[], progress=False, **kwargs):
    return v.Alert(type="info", text=True, prominent=True, icon=icon, children=[text, *children], **kwargs)


@react.component
def Error(text, icon="mdi-alert", children=[], **kwargs):
    return v.Alert(type="error", text=True, prominent=True, icon=icon, children=[text, *children], **kwargs)


@react.component
def Button(text: str = None, on_click=Callable[[], None], icon_name: str = None, children: list = [], click_event="click", **kwargs):
    if text:
        children = [text] + children
    if icon_name:
        children = [v.Icon(left=True, children=[icon_name])] + children
    btn = v.Btn(children=children, **kwargs)
    ipyvue.use_event(btn, click_event, lambda *_ignore: on_click and on_click())
    return btn


@react.component
def IconButton(icon_name: str = None, on_click=Callable[[], None], children: list = [], click_event="click", **kwargs):
    return Button(icon_name=icon_name, on_click=on_click, children=children, icon=True, click_event=click_event, **kwargs)


@react.component
def HTML(tag="div", unsafe_innerHTML=None, style: str = None, class_: str = None, **kwargs):
    attributes = dict(style=style)
    attributes["class"] = class_
    attributes = {**kwargs, **attributes}
    return solara.widgets.HTML.element(tag=tag, unsafe_innerHTML=unsafe_innerHTML, attributes=attributes)


@react.component
def VBox(children=[], grow=False):
    style = "flex-direction: column;"
    if grow:
        style += "flex-grow: 1;"
    return v.Card(class_="d-flex", style_=style, elevation=0, children=children)


@react.component
def HBox(children=[], grow=False):
    style = "flex-direction: row;"
    if grow:
        style += "flex-grow: 1;"
    return v.Card(class_="d-flex", style_=style, elevation=0, children=children)


@react.component
def GridFixed(columns=4, column_gap="10px", row_gap="10px", children=[], align_items="stretch", justify_items="stretch"):
    """

    See css grid spec:
    https://css-tricks.com/snippets/css/complete-guide-grid/
    """
    style = (
        f"display: grid; grid-template-columns: repeat({columns}, minmax(0, 1fr)); "
        + f"grid-column-gap: {column_gap}; grid-row-gap: {row_gap}; align-items: {align_items}; justify-items: {justify_items}"
    )
    return Div(style_=style, children=children)


@react.component
def Padding(size, children=[], grow=False):
    return v.Card(class_=f"pa-{size}", elevation=0, children=children)


@react.component
def AltairChart(chart, on_click=None, on_hover=None):
    import altair as alt

    with alt.renderers.enable("mimetype"):
        bundle = chart._repr_mimebundle_()[0]
        key = "application/vnd.vegalite.v4+json"
        if key not in bundle:
            raise KeyError(f"{key} not in mimebundle:\n\n{bundle}")
        spec = bundle[key]
        return solara.widgets.VegaLite.element(
            spec=spec, on_click=on_click, listen_to_click=on_click is not None, on_hover=on_hover, listen_to_hover=on_hover is not None
        )


@react.component
def FigurePlotly(fig, on_selection=None, on_click=None, on_hover=None, dependencies=None):
    from plotly.graph_objs._figurewidget import FigureWidget

    fig_element = FigureWidget.element()

    def update_data():
        fig_widget: FigureWidget = react.get_widget(fig_element)
        if on_selection:
            fig_widget.on_selection(on_selection)
        fig_widget.layout = fig.layout
        length = len(fig_widget.data)
        fig_widget.add_traces(fig.data)
        data = list(fig_widget.data)
        fig_widget.data = data[length:]
        for trace in fig_widget.data:
            if on_click:
                trace.on_click(on_click)
            if on_hover:
                trace.on_hover(on_hover)

    react.use_side_effect(update_data, dependencies or fig)
    return fig_element


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
    from mdit_py_plugins import container, deflist  # noqa: F401
    from mdit_py_plugins.footnote import footnote_plugin  # noqa: F401
    from mdit_py_plugins.front_matter import front_matter_plugin  # noqa: F401

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

    return HTML(unsafe_innerHTML=html)


@react.component
def Markdown(md_text: str):
    import markdown

    html = markdown.markdown(md_text, extensions=["pymdownx.highlight", "pymdownx.superfences", "pymdownx.emoji"])
    return HTML(unsafe_innerHTML=html)


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
