import solara
from matplotlib.figure import Figure


@solara.component
def Page():
    # do this instead of plt.figure()
    fig = Figure()
    ax = fig.subplots()
    ax.plot([1, 2, 3], [1, 4, 9])
    return solara.FigureMatplotlib(fig)


def test_render():
    box, rc = solara.render(Page(), handle_error=False)
    assert len(box.children) == 1
