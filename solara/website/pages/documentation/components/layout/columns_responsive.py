"""
# ColumnsResponsive

"""
import solara
import solara.lab
from solara.website.utils import apidoc

title = "ColumnsResponsive"

gutters = solara.reactive(True)
gutters_dense = solara.reactive(True)
wrap = solara.reactive(True)

children_count = solara.reactive(12)
columns_default = solara.reactive(6)
columns_small = solara.reactive(4)
columns_medium = solara.reactive(3)
columns_large = solara.reactive(2)
columns_xlarge = solara.reactive(1)


@solara.component
def Page():
    with solara.VBox() as main:
        with solara.Card("Controls"):
            solara.Checkbox(label="Wrap").connect(wrap)
            solara.Checkbox(label="Gutters").connect(gutters)
            solara.Checkbox(label="Dense gutters").connect(gutters_dense)
            solara.IntSlider("Children", max=20).connect(children_count)

            solara.Select("columns default", values=[1, 2, 3, 4, 6, 12]).connect(columns_default)  # type: ignore
            solara.Select("columns small", values=[1, 2, 3, 4, 6, 12]).connect(columns_small)  # type: ignore
            solara.Select("columns medium", values=[1, 2, 3, 4, 6, 12]).connect(columns_medium)  # type: ignore
            solara.Select("columns large", values=[1, 2, 3, 4, 6, 12]).connect(columns_large)  # type: ignore
            solara.Select("columns xlarge", values=[1, 2, 3, 4, 6, 12]).connect(columns_xlarge)  # type: ignore
        # taken from https://v2.vuetifyjs.com/en/styles/display/#display
        solara.HTML(
            "h2", unsafe_innerHTML=f"Current screensize is xsmall/default, each child is {columns_default.value} points wide", class_="ma-2 d-flex d-sm-none ma"
        )
        solara.HTML(
            "h2", unsafe_innerHTML=f"Current screensize is small, each child is {columns_small.value} points wide", class_="ma-2 d-none d-sm-flex d-md-none"
        )
        solara.HTML(
            "h2", unsafe_innerHTML=f"Current screensize is medium, each child is {columns_medium.value} points wide", class_="ma-2 d-none d-md-flex d-lg-none"
        )
        solara.HTML(
            "h2", unsafe_innerHTML=f"Current screensize is large, each child is {columns_large.value} points wide", class_="ma-2 d-none d-lg-flex d-xl-none"
        )
        solara.HTML("h2", unsafe_innerHTML=f"Current screensize is xlarge, each child is {columns_xlarge.value} points wide", class_="ma-2 d-none d-xl-flex")
        solara.Markdown("Change the screen size to see the effect of the different columns sizes.")
        with solara.ColumnsResponsive(
            default=columns_default.value,
            small=columns_small.value,
            medium=columns_medium.value,
            large=columns_large.value,
            xlarge=columns_xlarge.value,
            wrap=wrap.value,
            gutters=gutters.value,
            gutters_dense=gutters_dense.value,
        ):
            for i in range(children_count.value):
                solara.Text(f"{i}")
    return main


__doc__ += apidoc(solara.ColumnsResponsive.f)  # type: ignore
