import os
import traitlets
import ipyvuetify as v


class PivotTable(v.VuetifyTemplate):
    template_file = os.path.join(os.path.dirname(__file__), "vue/pivottable.vue")
    d = traitlets.Dict(default_value={'no': 'data'}).tag(sync=True)
    selected = traitlets.Dict(default_value=[]).tag(sync=True)


def watch():
    import ipyvue
    ipyvue.watch(os.path.dirname(__file__) + "/vue")
