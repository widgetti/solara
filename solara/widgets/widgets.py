import dataclasses
import os

import ipyvuetify as v
import ipywidgets
import traitlets

from ..datatypes import CellAction, ColumnAction

__all__ = [
    "DataTable",
    "VegaLite",
    "Navigator",
    "GridLayout",
    "HTML",
    "watch",
]


def _ensure_dict(d):
    if dataclasses.is_dataclass(d):
        return dataclasses.asdict(d)
    return d


def _drop_keys_from_list_of_mappings(drop):
    def closure(list_of_dicts, widget):
        return [{k: v for k, v in _ensure_dict(d).items() if k not in drop} for d in list_of_dicts]

    return closure


class DataTable(v.VuetifyTemplate):
    template_file = os.path.realpath(os.path.join(os.path.dirname(__file__), "vue/datatable.vue"))

    total_length = traitlets.CInt().tag(sync=True)
    checked = traitlets.List([]).tag(sync=True)  # indices of which rows are selected
    column_actions = traitlets.List(trait=traitlets.Instance(ColumnAction), default_value=[]).tag(
        sync=True, to_json=_drop_keys_from_list_of_mappings(["on_click"])
    )
    _column_actions_callbacks = traitlets.List(trait=traitlets.Callable(), default_value=[])
    cell_actions = traitlets.List(trait=traitlets.Instance(CellAction), default_value=[]).tag(sync=True, to_json=_drop_keys_from_list_of_mappings(["on_click"]))
    _cell_actions_callbacks = traitlets.List(trait=traitlets.Callable(), default_value=[])
    items = traitlets.Any().tag(sync=True)  # the data, a list of dict
    headers = traitlets.Any().tag(sync=True)
    headers_selections = traitlets.Any().tag(sync=True)
    options = traitlets.Any().tag(sync=True)
    items_per_page = traitlets.CInt(11).tag(sync=True)
    selections = traitlets.Any([]).tag(sync=True)
    selection_colors = traitlets.Any([]).tag(sync=True)
    selection_enabled = traitlets.Bool(True).tag(sync=True)
    highlighted = traitlets.Int(None, allow_none=True).tag(sync=True)
    scrollable = traitlets.Bool(False).tag(sync=True)

    # for use with scrollable, when used in the default UI
    height = traitlets.Unicode(None, allow_none=True).tag(sync=True)

    hidden_components = traitlets.List([]).tag(sync=False)

    def vue_on_column_action(self, data):
        header_value, action_index = data
        on_click = self._column_actions_callbacks[action_index]
        if on_click:
            on_click(header_value)

    def vue_on_cell_action(self, data):
        row, header_value, action_index = data
        on_click = self._cell_actions_callbacks[action_index]
        if on_click:
            on_click(header_value, row)


class VegaLite(v.VuetifyTemplate):
    template_file = os.path.realpath(os.path.join(os.path.dirname(__file__), "vue/vegalite.vue"))
    spec = traitlets.Dict().tag(sync=True)
    listen_to_click = traitlets.Bool(False).tag(sync=True)
    listen_to_hover = traitlets.Bool(False).tag(sync=True)
    on_click = traitlets.traitlets.Callable(None, allow_none=True)
    on_hover = traitlets.traitlets.Callable(None, allow_none=True)

    def vue_altair_click(self, *args):
        if self.on_click:
            self.on_click(*args)

    def vue_altair_hover(self, *args):
        if self.on_hover:
            self.on_hover(*args)


class Navigator(v.VuetifyTemplate):
    template_file = os.path.realpath(os.path.join(os.path.dirname(__file__), "vue/navigator.vue"))
    location = traitlets.Unicode(None, allow_none=True).tag(sync=True)


class GridLayout(v.VuetifyTemplate):
    template_file = os.path.join(os.path.dirname(__file__), "vue/gridlayout.vue")
    gridlayout_loaded = traitlets.Bool(False).tag(sync=True)
    items = traitlets.Union([traitlets.List(), traitlets.Dict()], default_value=[]).tag(sync=True, **ipywidgets.widget_serialization)
    grid_layout = traitlets.List(default_value=[]).tag(sync=True)
    draggable = traitlets.CBool(True).tag(sync=True)
    resizable = traitlets.CBool(True).tag(sync=True)


class HTML(v.VuetifyTemplate):
    template_file = os.path.realpath(os.path.join(os.path.dirname(__file__), "vue/html.vue"))
    tag = traitlets.Unicode("div").tag(sync=True)
    attributes = traitlets.Dict().tag(sync=True)
    unsafe_innerHTML = traitlets.Unicode(None, allow_none=True).tag(sync=True)


def watch():
    import ipyvue

    ipyvue.watch(os.path.realpath(os.path.dirname(__file__) + "/vue"))
