# isort: skip_file
from .components import *  # noqa: F401, F403


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
