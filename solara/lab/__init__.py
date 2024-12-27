# isort: skip_file
from .components import (
    ChatBox,
    ChatInput,
    ChatMessage,
    ConfirmationDialog,
    InputDate,
    InputDateRange,
    InputTime,
    ClickMenu,
    ContextMenu,
    Menu,
    Tab,
    Tabs,
    ThemeToggle,
    theme,
    use_dark_effective,
)
from .utils import cookies, headers
from ..lifecycle import on_kernel_start
from ..tasks import task, use_task, Task, TaskResult
from ..toestand import computed


__all__ = [
    "ChatBox",
    "ChatInput",
    "ChatMessage",
    "ConfirmationDialog",
    "InputDate",
    "InputDateRange",
    "InputTime",
    "ClickMenu",
    "ContextMenu",
    "Menu",
    "Tab",
    "Tabs",
    "ThemeToggle",
    "theme",
    "use_dark_effective",
    "cookies",
    "headers",
    "on_kernel_start",
    "task",
    "use_task",
    "Task",
    "TaskResult",
    "computed",
]


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
