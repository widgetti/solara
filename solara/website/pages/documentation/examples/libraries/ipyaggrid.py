"""
# ipyaggrid

[IPyAgGrid](https://github.com/widgetti/ipyaggrid) is a Jupyter widget for the [AG-Grid](https://www.ag-grid.com/) JavaScript library.

It is a feature-rich datagrid designed for enterprise applications.

To use it in a Solara component, requires a bit of manual wiring up of the dataframe and grid_options, as the widget does not have traits for these.

For more details, see [the IPywidget libraries Howto](https://solara.dev/docs/howto/ipywidget-libraries).


"""

from typing import cast

import ipyaggrid
import plotly.express as px

import solara

df = px.data.iris()
species = solara.reactive("setosa")
filter_species = solara.reactive(True)


@solara.component
def AgGrid(df, grid_options):
    """Convenient component wrapper around ipyaggrid.Grid"""

    def update_df():
        widget = cast(ipyaggrid.Grid, solara.get_widget(el))
        widget.grid_options = grid_options
        widget.update_grid_data(df)  # this also updates the grid_options

    # when df changes, grid_data will be update, however, ...
    el = ipyaggrid.Grid.element(grid_data=df, grid_options=grid_options)
    # grid_data and grid_options are not traits, so letting them update by reacton/solara has no effect
    # instead, we need to get a reference to the widget and call .update_grid_data in a use_effect
    solara.use_effect(update_df, [df, grid_options])
    return el


@solara.component
def Page():
    grid_options = {
        "columnDefs": [
            {"headerName": "Sepal Length", "field": "sepal_length"},
            {"headerName": "Species", "field": "species"},
        ]
    }

    df_filtered = df.query(f"species == {species.value!r}") if filter_species.value else df

    solara.Select("Filter species", value=species, values=["setosa", "versicolor", "virginica"])
    solara.Checkbox(label="Filter species", value=filter_species)
    AgGrid(df=df_filtered, grid_options=grid_options)
