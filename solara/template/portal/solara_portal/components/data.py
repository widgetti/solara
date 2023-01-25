import reacton.ipyvuetify as rv
import solara

from ..data import dfs


@solara.component
def DataCard(name):
    df = dfs[name].df
    with rv.Card(max_width="400px") as main:
        with solara.Link(f"/tabular/{name}"):
            rv.Img(height="250", src=dfs[name].image_url)
        rv.CardTitle(children=[dfs[name].title])
        with rv.CardText():
            solara.Markdown(f"*{len(df):,} rows*")
            with solara.Link(f"/tabular/{name}"):
                solara.Button("Open table view", text=True, icon_name="mdi-table")
    return main


@solara.component
def Overview():
    with solara.ColumnsResponsive(12) as main:
        with solara.Card("Datasets"):
            with solara.ColumnsResponsive(12, small=6, large=4):
                for name in dfs:
                    DataCard(name)
    return main
