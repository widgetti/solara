import threading
import time

import solara


def test_display_in_thread(kernel_context):
    rendered_in_thread = threading.Event()
    column = None
    render_count = 0

    @solara.component
    def Page():
        nonlocal column
        nonlocal render_count
        render_count += 1
        force_redraw = solara.use_reactive(0)

        def run():
            time.sleep(0.1)
            force_redraw.value = 1

        solara.use_thread(run, dependencies=[])

        def set_event():
            if force_redraw.value == 1:
                rendered_in_thread.set()

        solara.use_effect(set_event, dependencies=[force_redraw.value])

        s = solara.SliderInt("test")
        with solara.Column() as current_column:
            solara.display("test")
            solara.Button("test")
            solara.display(s)
        if force_redraw.value == 1:
            column = current_column

    _, rc = solara.render(Page(), handle_error=False)
    rendered_in_thread.wait(timeout=2)
    assert column is not None
    # assert render_count == 3
    assert len(column.kwargs["children"]) == 3
