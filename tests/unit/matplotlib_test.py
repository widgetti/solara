import reacton
from matplotlib.figure import Figure

import solara as sol


@reacton.component
def Page():
    # do this instead of plt.figure()
    fig = Figure()
    ax = fig.subplots()
    ax.plot([1, 2, 3], [1, 4, 9])
    return sol.FigureMatplotlib(fig)


def test_render():
    box, rc = reacton.render(Page(), handle_error=False)
    assert len(box.children) == 1
