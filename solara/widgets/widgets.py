import os
from typing import Dict, List, cast

import ipyvue
import ipyvuetify as v
import ipywidgets
import traitlets

from solara.util import IPYVUETIFY_V3

__all__ = [
    "VegaLite",
    "Navigator",
    "GridLayout",
    "HTML",
    "watch",
]


# Each template below has no Vuetify tags. The public class is a VuetifyTemplate, as before, and is used in
# Jupyter and in full mode. Its ...Vue base class has the same traits and template on ipyvue.VueTemplate, and is
# used on a Solara server without the vuetify frontend feature (see solara.server.frontend.template_class).


class VegaLiteVue(ipyvue.VueTemplate):
    template_file = os.path.realpath(os.path.join(os.path.dirname(__file__), "vue/vegalite.vue"))
    spec = traitlets.Dict().tag(sync=True)
    listen_to_click = traitlets.Bool(False).tag(sync=True)
    listen_to_hover = traitlets.Bool(False).tag(sync=True)
    on_click = traitlets.traitlets.Callable(None, allow_none=True)
    on_hover = traitlets.traitlets.Callable(None, allow_none=True)
    cdn = traitlets.Unicode(None, allow_none=True).tag(sync=True)

    def vue_altair_click(self, *args):
        if self.on_click is not None:
            self.on_click(*args)

    def vue_altair_hover(self, *args):
        if self.on_hover is not None:
            self.on_hover(*args)

    @traitlets.default("cdn")
    def _cdn(self):
        import solara.settings

        if not solara.settings.assets.proxy:
            return solara.settings.assets.cdn


class VegaLite(VegaLiteVue, v.VuetifyTemplate):
    pass


class NavigatorVue(ipyvue.VueTemplate):
    template_file = os.path.realpath(os.path.join(os.path.dirname(__file__), "vue/navigator.vue"))
    location = traitlets.Unicode(None, allow_none=True).tag(sync=True)


class Navigator(NavigatorVue, v.VuetifyTemplate):
    pass


class GridLayoutVue(ipyvue.VueTemplate):
    template_file = os.path.join(os.path.dirname(__file__), "vue/gridlayout_v3.vue" if IPYVUETIFY_V3 else "vue/gridlayout.vue")
    gridlayout_loaded = traitlets.Bool(False).tag(sync=True)
    items = traitlets.Union([traitlets.List(), traitlets.Dict()], default_value=[]).tag(sync=True, **ipywidgets.widget_serialization)
    grid_layout = traitlets.List(default_value=cast(List[Dict], [])).tag(sync=True)
    draggable = traitlets.CBool(True).tag(sync=True)
    resizable = traitlets.CBool(True).tag(sync=True)
    cdn = traitlets.Unicode(None, allow_none=True).tag(sync=True)
    on_layout_updated = traitlets.traitlets.Callable(None, allow_none=True)
    col_num = traitlets.Int(12).tag(sync=True)
    row_height = traitlets.Int(30).tag(sync=True)

    def vue_layout_updated(self, *args):
        if self.on_layout_updated is not None:
            self.on_layout_updated(*args)

    @traitlets.default("cdn")
    def _cdn(self):
        import solara.settings

        if not solara.settings.assets.proxy:
            return solara.settings.assets.cdn


class GridLayout(GridLayoutVue, v.VuetifyTemplate):
    pass


class HTMLVue(ipyvue.VueTemplate):
    template_file = os.path.realpath(os.path.join(os.path.dirname(__file__), "vue/html.vue"))
    tag = traitlets.Unicode("div").tag(sync=True)
    attributes = traitlets.Dict().tag(sync=True)
    unsafe_innerHTML = traitlets.Unicode(None, allow_none=True).tag(sync=True)


class HTML(HTMLVue, v.VuetifyTemplate):
    pass


def watch():
    ipyvue.watch(os.path.realpath(os.path.dirname(__file__) + "/vue"))
