"""# task

Decorator to turn a function or coroutine function into a task.
A task is a callable that will run the function in a separate thread for normal functions
or a asyncio task for a coroutine function.

The task callable does will only execute the function once when called multiple times,
and will cancel previous executions if the function is called again before the previous finished.


The wrapped function return value is available as the `.value` attribute of the task object.




"""
import solara
import solara.autorouting
import solara.lab
from solara.website.utils import apidoc

from . import NoPage

title = "task"
Page = NoPage
__doc__ += apidoc(solara.lab.task)  # type: ignore
