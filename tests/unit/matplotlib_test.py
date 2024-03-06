from matplotlib.figure import Figure

import solara
import solara.server.patch
from solara.server import kernel


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


def test_pylab(no_kernel_context):
    cleanup = solara.server.patch.patch_matplotlib()
    try:
        kernel_1 = kernel.Kernel()
        context_1 = solara.server.kernel_context.VirtualKernelContext(id="1", kernel=kernel_1, session_id="session-1")
        kernel_2 = kernel.Kernel()
        context_2 = solara.server.kernel_context.VirtualKernelContext(id="2", kernel=kernel_2, session_id="session-1")
        import matplotlib.pyplot as plt
        from matplotlib._pylab_helpers import Gcf

        assert len(Gcf.get_all_fig_managers()) == 0
        plt.figure()

        assert len(Gcf.get_all_fig_managers()) == 1

        default_color = (1, 1, 1, 0)
        white = "white"
        black = "black"
        assert plt.rcParams["figure.facecolor"] in [default_color, white]
        plt.style.use("default")
        assert plt.rcParams["figure.facecolor"] == white

        plt.style.use("dark_background")
        assert plt.rcParams["figure.facecolor"] == black

        with context_1:
            assert len(Gcf.get_all_fig_managers()) == 0
            plt.figure()
            assert plt.rcParams["figure.facecolor"] == black
            assert len(Gcf.get_all_fig_managers()) == 1
            plt.style.use("default")
            assert plt.rcParams["figure.facecolor"] == white

        assert plt.rcParams["figure.facecolor"] == black
        assert len(Gcf.get_all_fig_managers()) == 1
        plt.style.use("default")
        assert plt.rcParams["figure.facecolor"] == white

        with context_2:
            assert plt.rcParams["figure.facecolor"] == white
            assert len(Gcf.get_all_fig_managers()) == 0
            plt.figure()
            assert len(Gcf.get_all_fig_managers()) == 1
            plt.figure()
            assert len(Gcf.get_all_fig_managers()) == 2
            plt.style.use("dark_background")
            assert plt.rcParams["figure.facecolor"] == black
        with context_1:
            assert len(Gcf.get_all_fig_managers()) == 1
            assert plt.rcParams["figure.facecolor"] == white
        assert plt.rcParams["figure.facecolor"] == white

    finally:
        cleanup()
        context_1.close()
        context_2.close()
