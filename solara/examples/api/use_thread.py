import threading
from pathlib import Path
from typing import Optional, cast

from solara.kitchensink import react, sol, v, w

HERE = Path(__file__).parent
__doc__ = open(HERE / "use_thread.md").read()


@react.component
def UseThreadDemo():
    number, set_number = react.use_state(100423093)
    # the number that proofs it is not a prime
    proof, set_proof = react.use_state(cast(Optional[int], None))

    def work(cancelled: threading.Event):
        for i in range(3, number):
            reminder = number % i
            if reminder == 0:
                set_proof(i)
                return False
            # try commenting out this line to see the 'WAITING' state
            if i % 1000:  # only check every now and then
                if cancelled.is_set():
                    return
        return True

    # work will be cancelled/restarted every time the dependency changes
    result: sol.Result[bool] = sol.use_thread(work, dependencies=[number])

    with sol.VBox() as main:
        w.IntText(value=number, on_value=set_number)
        if result.state == sol.ResultState.FINISHED:
            if result.value:
                sol.Success(f"{number} is a prime!")
            else:
                sol.Error(f"{number} is not a prime")
                sol.Info(f"{number} can be divided by {proof} ")
        elif result.state == sol.ResultState.ERROR:
            sol.Error(f"Error occurred: {result.error}")
        else:
            sol.Info(f"Running... (status = {result.state})")
            v.ProgressCircular(indeterminate=True)
    return main


App = UseThreadDemo
