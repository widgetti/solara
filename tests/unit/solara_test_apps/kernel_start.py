import solara
import solara.lab


def test_callback():
    pass


solara.lab.on_kernel_start(test_callback)


@solara.component
def Page():
    solara.Text("Hello, World!")
