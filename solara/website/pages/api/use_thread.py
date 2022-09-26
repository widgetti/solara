import threading
import time
from pathlib import Path
from typing import Optional, cast

from solara.alias import reacton, rv, rw, sol

HERE = Path(__file__).parent
__doc__ = open(HERE / "use_thread.md").read()


@reacton.component
def Page():
    number, set_number = reacton.use_state(17)
    # the number that proofs it is not a prime
    proof, set_proof = reacton.use_state(cast(Optional[int], None))

    def work(cancelled: threading.Event):
        for i in range(3, number):
            reminder = number % i
            if reminder == 0:
                set_proof(i)
                return False
            # make it always take ~4 seconds
            time.sleep(4 / number)
        return True

    # work will be cancelled/restarted every time the dependency changes
    result: sol.Result[bool] = sol.use_thread(work, dependencies=[number])

    with sol.VBox() as main:
        rw.IntText(value=number, on_value=set_number)
        if result.state == sol.ResultState.FINISHED:
            if result.value:
                sol.Success(f"{number} is a prime!")
            else:
                sol.Error(f"{number} is not a prime, it can be divided by {proof} ")
        elif result.state == sol.ResultState.ERROR:
            sol.Error(f"Error occurred: {result.error}")
        else:
            sol.Info(f"Running... (status = {result.state})")
            rv.ProgressLinear(indeterminate=True)
    return main
