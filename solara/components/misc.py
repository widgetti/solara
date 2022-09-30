from typing import Any, Callable, List

import ipyvue as vue
import reacton
import reacton.ipyvuetify as v
import reacton.ipyvuetify as ipyvue
import solara
import solara.widgets

Navigator = reacton.core.ComponentWidget(solara.widgets.Navigator)
GridDraggable = reacton.core.ComponentWidget(solara.widgets.GridLayout)
# keep the old name for a while
GridLayout = GridDraggable


@solara.component
def ListItem(title, icon_name: str = None, children=[], value=None):
    if value is None:
        value = title
    if children:
        with v.ListItemContent() as main:
            v.ListItemTitle(children=[title])
            if icon_name is not None:
                with v.ListItemIcon():
                    v.Icon(children=[icon_name or ""])
        return v.ListGroup(children=children, v_slots=[{"name": "activator", "children": main}], no_action=True, value=True, append_icon=icon_name)
    else:
        with v.ListItem(value=value) as main:
            if icon_name is not None:
                with v.ListItemIcon():
                    v.Icon(children=[icon_name or ""])
            with v.ListItemContent():
                v.ListItemTitle(children=[title])
        return main


def ui_dropdown(label, value=None, options=["foo", "bar"], key=None, disabled=False, **kwargs):
    key = key or str(value) + str(label) + str(options)
    value, set_value = solara.use_state(value, key)

    def set_index(index):
        set_value(options[index])

    v.Select(v_model=value, label=label, items=options, on_v_model=set_value, clearable=True, disabled=disabled, **kwargs)
    return value


def ui_text(label, value="", key=None, clearable=False, hint="", disabled=False, **kwargs):
    key = key or str(value) + str(label) + str(hint)
    value, set_value = solara.use_state(value, key)
    v.TextField(v_model=value, label=label, on_v_model=set_value, clearable=clearable, hint=hint, disabled=disabled, **kwargs)
    return value


def ui_checkbox(label, value=True, key=None, disabled=False, **kwargs):
    key = key or str(value) + str(label)
    value, set_value = solara.use_state(value, key)
    v.Checkbox(v_model=value, label=label, on_v_model=set_value, **kwargs)
    return value


def ui_slider(value=1, label="", min=0, max=100, key=None, tick_labels=None, thumb_label=None, disabled=False, **kwargs):
    key = key or str(value) + str(label)
    value, set_value = solara.use_state(value, key)
    v.Slider(
        v_model=value,
        label=label,
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


@solara.component
def Card(title: str = None, elevation: int = 2, margin=2, children: List[reacton.core.Element] = []):
    with v.Card(elevation=elevation, class_=f"ma-{margin}") as main:
        if title:
            with v.CardTitle(
                children=[title],
            ):
                pass
        with v.CardText(children=children):
            pass
    return main


@solara.component
def Text(text):
    return vue.Html.element(tag="span", children=[text])


@solara.component
def Div(children=[], **kwargs):
    return vue.Html.element(tag="div", children=children, **kwargs)


@solara.component
def Preformatted(text, **kwargs):
    return vue.Html.element(tag="pre", children=[text], **kwargs)


@solara.component
def Warning(text, icon="mdi-alert", children=[], **kwargs):
    return v.Alert(type="warning", text=True, prominent=True, icon=icon, children=[text, *children], **kwargs)


@solara.component
def Info(text, icon="mdi-alert", children=[], progress=False, **kwargs):
    return v.Alert(type="info", text=True, prominent=True, icon=icon, children=[text, *children], **kwargs)


@solara.component
def Error(text, icon="mdi-alert", children=[], **kwargs):
    return v.Alert(type="error", text=True, prominent=True, icon=icon, children=[text, *children], **kwargs)


@solara.component
def Success(text, icon="mdi-alert", children=[], **kwargs):
    return v.Alert(type="success", text=True, prominent=True, icon=icon, children=[text, *children], **kwargs)


@solara.component
def Button(
    label: str = None,
    on_click: Callable[[], None] = None,
    icon_name: str = None,
    children: list = [],
    click_event="click",
    disabled=False,
    value=None,
    text=False,
    **kwargs,
):
    if label:
        children = [label] + children
    if icon_name:
        children = [v.Icon(left=bool(label), children=[icon_name])] + children
    btn = v.Btn(children=children, **kwargs, disabled=disabled, text=text)
    ipyvue.use_event(btn, click_event, lambda *_ignore: on_click and on_click())
    return btn


@solara.component
def IconButton(icon_name: str = None, on_click=Callable[[], None], children: list = [], click_event="click", **kwargs):
    return Button(icon_name=icon_name, on_click=on_click, children=children, icon=True, click_event=click_event, **kwargs)


@solara.component
def HTML(tag="div", unsafe_innerHTML=None, style: str = None, class_: str = None, **kwargs):
    attributes = dict(style=style)
    attributes["class"] = class_
    return solara.widgets.HTML.element(tag=tag, unsafe_innerHTML=unsafe_innerHTML, attributes=attributes)


@solara.component
def VBox(children=[], grow=True, align_items="stretch"):
    style = f"flex-direction: column; align-items: {align_items};"
    if grow:
        style += "flex-grow: 1;"
    return v.Sheet(class_="d-flex", style_=style, elevation=0, children=children)


@solara.component
def HBox(children=[], grow=True, align_items="stretch"):
    style = f"flex-direction: row; align-items: {align_items}; "
    if grow:
        style += "flex-grow: 1;"
    return v.Sheet(class_="d-flex", style_=style, elevation=0, children=children)


@solara.component
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


@solara.component
def Padding(size, children=[], grow=True):
    style = "flex-direction: row;"
    if grow:
        style += "flex-grow: 1;"
    return v.Sheet(class_=f"pa-{size}", style_=style, elevation=0, children=children)


@solara.component
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


@solara.component
def FigurePlotly(
    fig,
    on_selection: Callable[[Any], None] = None,
    on_deselect: Callable[[Any], None] = None,
    on_click: Callable[[Any], None] = None,
    on_hover: Callable[[Any], None] = None,
    on_unhover: Callable[[Any], None] = None,
    dependencies=None,
):
    from plotly.graph_objs._figurewidget import FigureWidget

    def on_points_callback(data):
        if data:
            event_type = data["event_type"]
            if event_type == "plotly_click":
                if on_click:
                    on_click(data)
            elif event_type == "plotly_hover":
                if on_hover:
                    on_hover(data)
            elif event_type == "plotly_unhover":
                if on_unhover:
                    on_unhover(data)
            elif event_type == "plotly_selected":
                if on_selection:
                    on_selection(data)
            elif event_type == "plotly_deselect":
                if on_deselect:
                    on_deselect(data)

    fig_element = FigureWidget.element(on__js2py_pointsCallback=on_points_callback)

    def update_data():
        fig_widget: FigureWidget = solara.get_widget(fig_element)
        fig_widget.layout = fig.layout

        length = len(fig_widget.data)
        fig_widget.add_traces(fig.data)
        data = list(fig_widget.data)
        fig_widget.data = data[length:]

    solara.use_effect(update_data, dependencies or fig)
    return fig_element


@solara.component
def Code(path, path_header=None):
    path_header = path_header or path
    with open(path) as f:
        code = f.read()
    md = solara.Markdown(
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
