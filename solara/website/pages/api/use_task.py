"""# use_task

A hook that allows you to run code in the background, with the UI available to the user. This is useful for long running tasks, like downloading data.

Note that unlike with the `@task` decorator, the result is not globally shared, but only available to the component that called `use_task`.

"""
import solara
import solara.autorouting
import solara.lab
from solara.website.utils import apidoc

from . import NoPage

title = "task"
Page = NoPage
__doc__ += apidoc(solara.lab.task)  # type: ignore
