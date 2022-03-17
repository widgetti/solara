import os
import traitlets
import ipyvuetify as v
import copy


class PivotTable(v.VuetifyTemplate):
    template_file = os.path.realpath(os.path.join(os.path.dirname(__file__), "vue/pivottable.vue"))
    d = traitlets.Dict(default_value={"no": "data"}).tag(sync=True)
    selected = traitlets.Dict(default_value=[]).tag(sync=True)


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
