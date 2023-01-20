"""
# Columns

"""
import solara
import solara.lab
from solara.website.utils import apidoc

gutters = solara.lab.Reactive[bool](True)
gutters_dense = solara.lab.Reactive[bool](True)


@solara.component
def Page():
    gutters.use()
    gutters_dense.use()

    with solara.Columns([1, 2, 1], gutters=gutters.value, gutters_dense=gutters_dense.value) as main:
        with solara.Card("Left", margin=0):
            solara.Checkbox(label="Gutters").connect(gutters)
            solara.Checkbox(label="Dense gutters").connect(gutters_dense)
        with solara.Card("Middle", margin=0):
            solara.Markdown("This column has a relative width of 2, the columns to the left and right have a relative width of 1.")
        with solara.Card("Right", margin=0):
            solara.Markdown("This column has a relative width of 1, the columns to the left has a relative width of 2.")
    return main


__doc__ += apidoc(solara.Columns.f)  # type: ignore
