from solara.kitchensink import react, sol, v


@react.component
def Details(summary="Summary", children=[], expand=False):
    expand, set_expand = sol.use_state_or_update(expand)

    def on_v_model(v_model):
        if v_model is None:  # collapsed:
            set_expand(False)
        elif v_model == 0:
            set_expand(True)
        else:
            raise RuntimeError(f"v_model has odd value: {v_model}")

    with v.ExpansionPanels(v_model=0 if expand else None, on_v_model=on_v_model) as main:
        with v.ExpansionPanel():
            v.ExpansionPanelHeader(children=[summary])
            v.ExpansionPanelContent(children=children)
    return main
