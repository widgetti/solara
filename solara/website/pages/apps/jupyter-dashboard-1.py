from pathlib import Path

import folium
import folium.plugins
import matplotlib.pyplot as plt
import pandas as pd

import solara

districts = solara.reactive(
    ["Bayview", "Northern"],
)
categories = solara.reactive(["Vandalism", "Assault", "Robbery"])
limit = solara.reactive(100)


ROOT = Path(solara.__file__).parent / "website" / "pages" / "docs" / "content" / "04-tutorial"
path = ROOT / Path("SF_crime_sample.csv.gz")
url = "https://raw.githubusercontent.com/widgetti/solara/master/solara/website/pages/docs/content/04-tutorial/SF_crime_sample.csv"

if path.exists():
    df_crime = pd.read_csv(path)
else:
    df_crime = pd.read_csv(url)

df_crime


df_crime["Category"] = df_crime["Category"].str.title()
df_crime["PdDistrict"] = df_crime["PdDistrict"].str.title()


def crime_filter(df, district_values, category_values):
    df_dist = df.loc[df["PdDistrict"].isin(district_values)]
    df_category = df_dist.loc[df_dist["Category"].isin(category_values)]
    return df_category


def crime_charts(df):
    cat_unique = df["Category"].value_counts()
    cat_unique = cat_unique.reset_index()

    dist_unique = df["PdDistrict"].value_counts()
    dist_unique = dist_unique.reset_index()

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 10))

    ax1.bar(cat_unique["Category"], cat_unique["count"])
    ax1.set_title("Amount of Criminal Case Based on Category")
    ax2.bar(dist_unique["PdDistrict"], dist_unique["count"])
    ax2.set_title("Amount of Criminal Case in Selected District")

    # this does not work on solara yet: https://github.com/widgetti/solara/issues/399
    # display(fig)
    # plt.close(fig)
    solara.FigureMatplotlib(fig)


def crime_map(df):
    latitude = 37.77
    longitude = -122.42

    sanfran_map = folium.Map(height=400, location=[latitude, longitude], zoom_start=12)

    incidents = folium.plugins.MarkerCluster().add_to(sanfran_map)

    # loop through the dataframe and add each data point to the mark cluster
    for (
        lat,
        lng,
        label,
    ) in zip(df.Y, df.X, df.Category):
        folium.Marker(
            location=[lat, lng],
            icon=None,
            popup=label,
        ).add_to(incidents)

    # show map
    solara.display(sanfran_map)


@solara.component
def View():
    dff = crime_filter(df_crime, districts.value, categories.value)
    row_count = len(dff)
    if row_count > limit.value:
        solara.Warning(f"Only showing the first {limit.value} of {row_count:,} crimes on map")
    with solara.Column(style={"max-height": "400px"}):
        crime_map(dff.iloc[: limit.value])
    if row_count > 0:
        crime_charts(dff)
    else:
        solara.Warning("You filtered out all the data, no charts shown")


@solara.component
def Controls():
    solara.SelectMultiple("District", all_values=[str(k) for k in df_crime["PdDistrict"].unique().tolist()], values=districts)  # type: ignore
    solara.SelectMultiple("Category", all_values=[str(k) for k in df_crime["Category"].unique().tolist()], values=categories)  # type: ignore
    solara.Text("Maximum number of rows to show on map")
    solara.SliderInt("", value=limit, min=1, max=1000)


@solara.component
def Page():
    with solara.Sidebar():
        Controls()
    View()


# only needed on the solara website itself
@solara.component
def Layout(children):
    route, routes = solara.use_route()
    return solara.AppLayout(children=children)
