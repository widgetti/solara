import os
import traitlets
import ipyvuetify as v
import copy


class PivotTable(v.VuetifyTemplate):
    template_file = os.path.realpath(os.path.join(os.path.dirname(__file__), "vue/pivottable.vue"))
    d = traitlets.Dict(default_value={"no": "data"}).tag(sync=True)
    selected = traitlets.Dict(default_value=[]).tag(sync=True)


class DataTable(v.VuetifyTemplate):
    template_file = os.path.realpath(os.path.join(os.path.dirname(__file__), "vue/datatable.vue"))

    total_length = traitlets.CInt().tag(sync=True)
    checked = traitlets.List([]).tag(sync=True)  # indices of which rows are selected
    actions = traitlets.List([]).tag(sync=True)  # indices of which rows are selected
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


def watch():
    import ipyvue

    ipyvue.watch(os.path.realpath(os.path.dirname(__file__) + "/vue"))
