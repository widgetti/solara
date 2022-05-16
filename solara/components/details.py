from solara.kitchensink import react, v


@react.component
def Details(summary="Summary", children=[], expand=False):
    expand, set_expand = react.use_state(expand)
    with v.ExpansionPanels(v_model=0 if expand else None, on_v_model=set_expand) as main:
        with v.ExpansionPanel():
            v.ExpansionPanelHeader(children=[summary])
            v.ExpansionPanelContent(children=children)
    return main
