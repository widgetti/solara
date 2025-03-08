import solara
import solara.lab
import unittest.mock


started = unittest.mock.Mock()
cleaned = unittest.mock.Mock()


def app_start():
    started()
    return cleaned


solara.lab.on_app_start(app_start)


@solara.component
def Page():
    solara.Text("Hello, World!")
