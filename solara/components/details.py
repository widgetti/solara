import solara
from solara.alias import rv


@solara.component
def Details(summary="Summary", children=[], expand=False):
    """Creates an expandable/collapsible section with a summary and additional children content

    ```solara
    import solara


    show_message = solara.reactive(True)
    disable = solara.reactive(False)


    @solara.component
    def Page():
        summary_text = "Click to expand for more details"
        additional_content = [
            "Additional detail 1",
            "Additional detail 2",
            "Additional detail 3"
        ]

        solara.Details(
            summary=summary_text,
            children=additional_content,
            expand=False
        )

    ```


    ## Arguments:

    * summary: String showing the summary text for the expandable section: Defaults "Summary"
    * children: List showing the children content of the expandable section: Defaults to an Empty list
    * expand: Boolean showing if the section is expanded or collapsed: Defaults to False
    """

    expand, set_expand = solara.use_state_or_update(expand)

    def on_v_model(v_model):
        if v_model is None:  # collapsed:
            set_expand(False)
        elif v_model == 0:
            set_expand(True)
        else:
            raise RuntimeError(f"v_model has odd value: {v_model}")

    with rv.ExpansionPanels(v_model=0 if expand else None, on_v_model=on_v_model) as main:
        with rv.ExpansionPanel():
            rv.ExpansionPanelHeader(children=[summary])
            rv.ExpansionPanelContent(children=children)
    return main
