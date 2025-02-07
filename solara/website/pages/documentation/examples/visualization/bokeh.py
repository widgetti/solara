"""# Scatter plot using Bokeh

This example shows how to use Bokeh to create a scatter plot and a select box to do some filtering.

Inspired by the bokeh documentation.
"""

from bokeh.models import ColorBar, DataRange1d, LinearColorMapper

from bokeh.plotting import figure, ColumnDataSource
from bokeh.sampledata import penguins

import solara

title = "Scatter plot using Bokeh"

df = penguins.data


@solara.component
def Page():
    all_species = df["species"].unique().tolist()
    species = solara.use_reactive(all_species[0])
    with solara.Div() as main:
        solara.Select(label="Species", value=species, values=all_species)
        dff = df[df["species"] == species.value]

        source = ColumnDataSource(
            data={
                "x": dff["bill_length_mm"].values,
                "y": dff["bill_depth_mm"].values,
                "z": dff["body_mass_g"].values,
            }
        )

        # make a figure
        p = figure(
            x_range=DataRange1d(), y_range=DataRange1d(), x_axis_label="Bill length [mm]", y_axis_label="Bill depth [mm]", width_policy="max", height=400
        )

        # add a scatter, colorbar, and mapper
        mapper = LinearColorMapper(palette="Viridis256", low=dff["body_mass_g"].min(), high=dff["body_mass_g"].max())
        cb = ColorBar(color_mapper=mapper, title="Body mass [g]")
        p.scatter(source=source, x="x", y="y", marker="circle", size=8, fill_color={"field": "z", "transform": mapper})
        p.add_layout(cb, "right")

        solara.lab.FigureBokeh(p, dark_theme="carbon", dependencies=[species])
    return main
