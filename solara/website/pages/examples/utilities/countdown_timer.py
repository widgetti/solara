"""# Countdown timer.

This example shows how to use [use_thread](/api/use_thread) to create a countdown timer.

The UI code demonstrates a lot of conditional rendering.

"""

import time

import solara
from solara.alias import rv


@solara.component
def Page():
    seconds, set_seconds = solara.use_state(5)
    running, set_running = solara.use_state(False)
    duration, set_duration = solara.use_state(seconds)

    def on_duration(duration):
        try:
            set_duration(int(duration))
            set_seconds(int(duration))
        except ValueError:
            pass

    def run_timer():
        if running:
            time_start = time.time()
            next_tick = time_start + 1
            i = seconds
            while i:
                # instead of sleeping for 1 second, we sleep until the next second
                # this takes into account overhead and makes the timer more accurate
                time.sleep(max(0, next_tick - time.time()))
                i -= 1
                set_seconds(i)
                next_tick += 1
            set_running(False)

    solara.use_thread(run_timer, dependencies=[duration, running])

    with solara.VBox() as main:
        if not running:
            if duration < 1:
                solara.Error("Duration must be at least 1 second")
            else:
                solara.Markdown(f"# Timer set to {seconds} seconds")
        else:
            if seconds:
                solara.Markdown(f"# {seconds} seconds left")
            else:
                solara.solara.Markdown("# Time's up!")
        rv.TextField(type="number", v_model=duration, on_v_model=on_duration, disabled=running)
        with solara.HBox():
            if running:
                solara.Button("Stop", on_click=lambda: set_running(False), icon_name="mdi-stop")
            else:
                if duration != seconds:
                    solara.Button("Reset", on_click=lambda: set_seconds(duration), icon_name="mdi-restart")
                else:
                    solara.Button("Start", on_click=lambda: set_running(True), icon_name="mdi-play", disabled=seconds < 1)
    return main
