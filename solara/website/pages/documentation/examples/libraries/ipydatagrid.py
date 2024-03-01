"""
# ipydatagrid

[ipydatagrid](https://github.com/bloomberg/ipydatagrid) is a Jupyter widget developed by Bloomberg which describes itself as a
"Fast Datagrid widget for the Jupyter Notebook and JupyterLab".

To use it in a Solara component requires a bit of manual wiring up of the dataframe, as this widget does not use a trait for this
(and the property name does not match the constructor argument).

For more details, see [the IPywidget libraries Howto](https://solara.dev/docs/howto/ipywidget-libraries).


"""

from typing import Dict, List, cast

import ipydatagrid
import plotly.express as px

import solara

df = px.data.iris()
species = solara.reactive("setosa")
filter_species = solara.reactive(True)


@solara.component
def DataGrid(df, **kwargs):
    """Convenient component wrapper around ipydatagrid.DataGrid"""

    def update_df():
        widget = cast(ipydatagrid.DataGrid, solara.get_widget(el))
        # This is needed to update the dataframe, see
        #  https://solara.dev/docs/howto/ipywidget-libraries for details
        widget.data = df

    el = ipydatagrid.DataGrid.element(dataframe=df, **kwargs)  # does NOT change when df changes
    # we need to use .data instead (on the widget) to update the dataframe
    solara.use_effect(update_df, [df])
    return el


@solara.component
def Page():
    selections: solara.Reactive[List[Dict]] = solara.use_reactive([])
    df_filtered = df.query(f"species == {species.value!r}") if filter_species.value else df

    with solara.Card("ipydatagrid demo", style={"width": "700px"}):
        solara.Select("Filter species", value=species, values=["setosa", "versicolor", "virginica"])
        solara.Checkbox(label="Filter species", value=filter_species)
        DataGrid(df=df_filtered, selection_mode="row", selections=selections.value, on_selections=selections.set)
        if selections.value:
            with solara.Column():
                solara.Text(f"Selected rows: {selections.value!r}")
                solara.Button("Clear selections", on_click=lambda: selections.set([]))
