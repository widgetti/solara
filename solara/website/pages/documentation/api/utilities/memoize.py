"""#Memoize

"""
import time

import solara
import solara.lab
from solara.website.utils import apidoc

# make sure the cache is only created once
storage = solara.cache.Memory(max_items=2)


@solara.component
def Page():
    x, set_x = solara.use_state(5)

    @solara.memoize(storage=storage)
    def long_running_function(x: int) -> int:
        """This function takes a long time to run."""
        time.sleep(3)
        return x**2

    result = long_running_function.use_thread(x)

    with solara.Card("Expensive computation") as main:
        solara.Markdown("We cache 2 values. Each computation takes 3 seconds. If you go back to a cached value, you will see the result immediately.")
        solara.IntSlider("x", value=x, on_value=set_x)
        if result.state == solara.ResultState.FINISHED:
            solara.Markdown(f"Square of {x} is {result.value}")
        else:
            solara.Markdown("Running...")
    return main


__doc__ += apidoc(solara.memoize)  # type: ignore
