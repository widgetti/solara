"""# Task

A global way to run code in the background, with the UI available to the user. This is useful for long running tasks, like downloading data.

The task decorator turns a function or coroutine function into a task object.
A task is a callable that will run the function in a separate thread for normal functions
or a asyncio task for a coroutine function.

The task object will execute the function only once per virtual kernel. When called multiple times,
the a previously started run will be cancelled.

The Result object is wrapped as a reactive variable in the `.result` attribute of the task object, so to access the underlying value, use `.result.value`.

The return value of the function is available as the `.value` attribute of the result object, meaning it's accessible as `.result.value.value`. While
a demonstation of composability, this is not very readable, so you can also use `.value` property to access the return value of the function.

## Task object

 * `.result`: A reactive variable wrapping the result object.
 * `.value`: Alias for `.result.value.value`
 * `.error`: Alias for `.result.value.error`
 * `.state`: Alias for `.result.value.state`
 * `.cancel()`: Cancels the task.



"""
import solara
import solara.autorouting
import solara.lab
from solara.website.utils import apidoc

from . import NoPage

title = "task"
Page = NoPage
__doc__ += apidoc(solara.lab.task)  # type: ignore
