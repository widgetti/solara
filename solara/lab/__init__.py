# isort: skip_file
from .components import *  # noqa: F401, F403
from .utils import cookies, headers  # noqa: F401, F403
from ..lifecycle import on_kernel_start  # noqa: F401
from ..tasks import task as _task, use_task as _use_task, Task as _Task, TaskResult as _TaskResult
from ..toestand import computed  # noqa: F401
from ..util import deprecated


@deprecated("solara.lab.task has been moved out of the lab namespace, use solara.task instead")
def task(*args, **kwargs):
    _task(*args, **kwargs)


@deprecated("solara.lab.use_task has been moved out of the lab namespace, use solara.use_task instead")
def use_task(*args, **kwargs):
    return _use_task(*args, **kwargs)


@deprecated("solara.lab.Task has been moved out of the lab namespace, use solara.Task instead")
class Task(_Task):
    pass


@deprecated("solara.lab.TaskResult has been moved out of the lab namespace, use solara.TaskResult instead")
class TaskResult(_TaskResult):
    pass


def __getattr__(name):
    # for backwards compatibility
    from solara.components.cross_filter import (  # noqa: F401
        CrossFilterDataFrame,
        CrossFilterReport,
        CrossFilterSelect,
        CrossFilterSlider,
    )
    from solara.toestand import Reactive, Ref, State  # noqa: F401

    if name == "CrossFilterDataFrame":
        return CrossFilterDataFrame
    elif name == "CrossFilterReport":
        return CrossFilterReport
    elif name == "CrossFilterSelect":
        return CrossFilterSelect
    elif name == "CrossFilterSlider":
        return CrossFilterSlider
    elif name == "Reactive":
        return Reactive
    elif name == "Ref":
        return Ref
    elif name == "State":
        return State
    else:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
