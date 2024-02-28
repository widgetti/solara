# isort: skip_file
from .components import *  # noqa: F401, F403
from .utils import cookies, headers  # noqa: F401, F403
from ..server.kernel_context import on_kernel_start  # noqa: F401
from ..tasks import task, use_task, Task, TaskResult  # noqa: F401, F403
from ..toestand import computed  # noqa: F401


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
