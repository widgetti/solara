from typing import Optional, Union

import reacton.ipyvuetify as v

import solara


@solara.component
def Tooltip(
    tooltip=Union[str, solara.Element],
    children=[],
    color: Optional[str] = None,
):
    """A tooltip that is shown when you hover above an element.

    Not all components support tooltips, in case it does not work,
    try wrapping the element in a `Column` or `Row`.

    ```solara
    import solara

    @solara.component
    def Page():
        with solara.Tooltip("This is a tooltip over a button"):
            solara.Button("Hover me")
        with solara.Tooltip("This is a tooltip over a text"):
            solara.Text("Hover me")
        info = solara.Info("Any component is supported as tooltip.")
        with solara.Tooltip(info, color="white"):
            with solara.Column():
                solara.Markdown("# Lorem ipsum\\n\\nDolor sit amet")
    ```

    ## Arguments

     * `tooltip`: the text, or element to display on hover.
     * `children`: the element to display the tooltip over.
     * `color`: the color of the tooltip (if None, the default color).

    """

    def set_v_on():
        for child in children:
            widget = solara.get_widget(child)
            # this only works on vue/vuetify components
            widget.v_on = "tooltip.on"  # type: ignore

    solara.use_effect(set_v_on, children)

    return v.Tooltip(
        bottom=True,
        v_slots=[
            {
                "name": "activator",
                "variable": "tooltip",
                "children": children,
            }
        ],
        color=color,
        children=[tooltip],
    )
