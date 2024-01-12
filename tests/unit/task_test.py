import asyncio
import time

import ipyvuetify as v
from reacton import ipywidgets as w

import solara.tasks
from solara.server import kernel, kernel_context
from solara.tasks import use_task
from solara.toestand import Computed


@solara.tasks.task
def something(count: int, delay: float = 1):
    time.sleep(delay)
    return "42" * count


@solara.component
def ComputeButton(count, delay: float = 1, on_render=lambda: None):
    solara.Button("Run", on_click=lambda: something(count, delay))
    on_render()
    # print(something.result.value)
    if something.result.value:
        if something.state == solara.ResultState.RUNNING:
            solara.Info("running")
        elif something.state == solara.ResultState.FINISHED:
            solara.Info("Done: " + str(something.value))
        elif something.state == solara.ResultState.ERROR:
            solara.Info("Error: " + str(something.error))
        else:
            solara.Info("Cancelled")


@solara.component
def Page():
    ComputeButton(2)
    ComputeButton(3)


cancel_square = False


@solara.tasks.task
def square(value: float):
    if cancel_square:
        square.cancel()
    return value**2


@solara.component
def SquareButton(value, on_render=lambda: None):
    solara.Button("Run", on_click=lambda: square(value))
    on_render()
    if square.result.value:
        if square.state == solara.ResultState.RUNNING:
            solara.Info("running")
        elif square.state == solara.ResultState.FINISHED:
            solara.Info("Done: " + str(square.value))
        elif square.state == solara.ResultState.ERROR:
            solara.Info("Error: " + str(square.error))
        else:
            solara.Info("Cancelled")


def test_task_basic():
    results = []

    def collect():
        results.append((square.state, square.value))

    box, rc = solara.render(SquareButton(3, on_render=collect), handle_error=False)
    button = rc.find(v.Btn, children=["Run"]).widget
    button.click()
    assert square._last_finished_event  # type: ignore
    square._last_finished_event.wait()  # type: ignore
    assert results == [
        (solara.ResultState.INITIAL, None),
        (solara.ResultState.STARTING, None),
        (solara.ResultState.RUNNING, None),
        (solara.ResultState.FINISHED, 9),
    ]
    results.clear()
    rc.render(SquareButton(2, on_render=collect))
    button = rc.find(v.Btn, children=["Run"]).widget
    button.click()
    square._last_finished_event.wait()  # type: ignore
    assert results == [
        # extra finished due to the rc.render call
        (solara.ResultState.FINISHED, 9),
        (solara.ResultState.STARTING, 9),
        (solara.ResultState.RUNNING, 9),
        (solara.ResultState.FINISHED, 4),
    ]


# async version

cancel_square_async = False


@solara.tasks.task
async def square_async(value: float):
    if cancel_square_async:
        square_async.cancel()
    return value**2


@solara.component
def SquareButtonAsync(value, on_render=lambda: None):
    solara.Button("Run", on_click=lambda: square_async(value))
    on_render()
    if square_async.result.value:
        if square_async.state == solara.ResultState.RUNNING:
            solara.Info("running")
        elif square_async.state == solara.ResultState.FINISHED:
            solara.Info("Done: " + str(square_async.value))
        elif square_async.state == solara.ResultState.ERROR:
            solara.Info("Error: " + str(square_async.error))
        else:
            solara.Info("Cancelled")


async def test_task_basic_async():
    results = []

    def collect():
        results.append((square_async.state, square_async.value))

    box, rc = solara.render(SquareButtonAsync(3, on_render=collect), handle_error=False)
    button = rc.find(v.Btn, children=["Run"]).widget
    button.click()
    assert square_async.current_task  # type: ignore
    await square_async.current_task  # type: ignore
    assert results == [
        (solara.ResultState.INITIAL, None),
        (solara.ResultState.STARTING, None),
        (solara.ResultState.RUNNING, None),
        (solara.ResultState.FINISHED, 9),
    ]
    results.clear()
    rc.render(SquareButtonAsync(2, on_render=collect))
    button = rc.find(v.Btn, children=["Run"]).widget
    button.click()
    await square_async.current_task  # type: ignore
    assert results == [
        # extra finished due to the rc.render call
        (solara.ResultState.FINISHED, 9),
        (solara.ResultState.STARTING, 9),
        (solara.ResultState.RUNNING, 9),
        (solara.ResultState.FINISHED, 4),
    ]


def test_task_two():
    results2 = []
    results3 = []
    # ugly reset
    square.last_value = None

    def collect2():
        results2.append((square.state, square.value))

    def collect3():
        results3.append((square.state, square.value))

    @solara.component
    def Test():
        SquareButton(2, on_render=collect2)
        SquareButton(3, on_render=collect3)

    box, rc = solara.render(Test(), handle_error=False)
    button = rc.find(v.Btn, children=["Run"])[0].widget
    button.click()
    assert square._last_finished_event  # type: ignore
    square._last_finished_event.wait()  # type: ignore
    assert (
        results2
        == results3
        == [
            (solara.ResultState.INITIAL, None),
            (solara.ResultState.STARTING, None),
            (solara.ResultState.RUNNING, None),
            (solara.ResultState.FINISHED, 4),
        ]
    )
    assert len(rc.find(children=["Done: 4"])) == 2

    # now we press the second button
    results2.clear()
    results3.clear()
    button = rc.find(v.Btn, children=["Run"])[1].widget
    button.click()
    assert square._last_finished_event  # type: ignore
    square._last_finished_event.wait()  # type: ignore
    assert (
        results2
        == results3
        == [
            # not a finished event, because we don't render from the start
            (solara.ResultState.STARTING, 4),
            (solara.ResultState.RUNNING, 4),
            (solara.ResultState.FINISHED, 9),
        ]
    )
    assert len(rc.find(children=["Done: 9"])) == 2


def test_task_cancel_retry():
    global cancel_square
    results = []

    # ugly reset
    square.last_value = None

    def collect():
        results.append((square.state, square.value))

    box, rc = solara.render(SquareButton(5, on_render=collect), handle_error=False)
    button = rc.find(v.Btn, children=["Run"]).widget
    cancel_square = True
    try:
        button.click()
        assert square._last_finished_event  # type: ignore
        square._last_finished_event.wait()  # type: ignore
        assert results == [
            (solara.ResultState.INITIAL, None),
            (solara.ResultState.STARTING, None),
            (solara.ResultState.RUNNING, None),
            (solara.ResultState.CANCELLED, None),
        ]
    finally:
        cancel_square = False
    results.clear()
    square.retry()
    square._last_finished_event.wait()  # type: ignore
    assert results == [
        (solara.ResultState.STARTING, None),
        (solara.ResultState.RUNNING, None),
        (solara.ResultState.FINISHED, 5**2),
    ]


async def test_task_async_cancel_retry():
    global cancel_square_async
    results = []

    # ugly reset
    square_async.last_value = None

    def collect():
        results.append((square_async.state, square_async.value))

    box, rc = solara.render(SquareButtonAsync(5, on_render=collect), handle_error=False)
    button = rc.find(v.Btn, children=["Run"]).widget
    cancel_square_async = True
    try:
        button.click()
        assert square_async.current_task  # type: ignore
        await square_async.current_task  # type: ignore
        assert results == [
            (solara.ResultState.INITIAL, None),
            (solara.ResultState.STARTING, None),
            (solara.ResultState.RUNNING, None),
            (solara.ResultState.CANCELLED, None),
        ]
    finally:
        cancel_square_async = False
    results.clear()
    square_async.retry()
    await square_async.current_task  # type: ignore
    assert results == [
        (solara.ResultState.STARTING, None),
        (solara.ResultState.RUNNING, None),
        (solara.ResultState.FINISHED, 5**2),
    ]


def test_task_scopes(no_kernel_context):
    results1 = []
    results2 = []

    def collect1():
        results1.append((something.state, something.value))

    def collect2():
        results2.append((something.state, something.value))

    kernel1 = kernel.Kernel()
    kernel2 = kernel.Kernel()
    assert kernel_context.current_context[kernel_context.get_current_thread_key()] is None

    context1 = kernel_context.VirtualKernelContext(id="toestand-1", kernel=kernel1, session_id="session-1")
    context2 = kernel_context.VirtualKernelContext(id="toestand-2", kernel=kernel2, session_id="session-2")

    with context1:
        box1, rc1 = solara.render(ComputeButton(5, on_render=collect1), handle_error=False)
        button1 = rc1.find(v.Btn, children=["Run"]).widget

    with context2:
        box2, rc2 = solara.render(ComputeButton(5, on_render=collect2), handle_error=False)
        button2 = rc2.find(v.Btn, children=["Run"]).widget

    with context1:
        button1.click()
        finished_event1 = something._last_finished_event  # type: ignore
        assert finished_event1

    with context2:
        assert something._last_finished_event is not finished_event1  # type: ignore
        assert something._last_finished_event is None  # type: ignore
        something.cancel()

    finished_event1.wait()
    assert results1 == [
        (solara.ResultState.INITIAL, None),
        (solara.ResultState.STARTING, None),
        (solara.ResultState.RUNNING, None),
        (solara.ResultState.FINISHED, "4242424242"),
    ]
    # results1.clear()
    assert results2 == [(solara.ResultState.INITIAL, None)]

    with context2:
        button2.click()
        finished_event2 = something._last_finished_event  # type: ignore
        assert finished_event2
    finished_event2.wait()
    assert results2 == [
        (solara.ResultState.INITIAL, None),
        (solara.ResultState.STARTING, None),
        (solara.ResultState.RUNNING, None),
        (solara.ResultState.FINISHED, "4242424242"),
    ]


def test_task_and_computed(no_kernel_context):
    @Computed
    def square_minus_one():
        # breakpoint()
        return square.value - 1

    kernel1 = kernel.Kernel()
    kernel2 = kernel.Kernel()
    assert kernel_context.current_context[kernel_context.get_current_thread_key()] is None

    context1 = kernel_context.VirtualKernelContext(id="t1", kernel=kernel1, session_id="session-1")
    context2 = kernel_context.VirtualKernelContext(id="t2", kernel=kernel2, session_id="session-2")

    with context1:
        r1 = square.result
        assert len(square.result._storage.listeners2["t1"]) == 0
        square(5)
        assert square._last_finished_event  # type: ignore
        square._last_finished_event.wait()  # type: ignore
        # accessing will add it to the listeners
        assert len(square.result._storage.listeners2["t1"]) == 0
        assert square_minus_one.value == 24
        assert len(square.result._storage.listeners2["t1"]) == 1
        square_minus_one._auto_subscriber.value.reactive_used == {square.value}

    with context2:
        r2 = square.result
        assert len(square.result._storage.listeners2["t2"]) == 0
        square(6)
        assert square._last_finished_event  # type: ignore
        square._last_finished_event.wait()  # type: ignore
        assert len(square.result._storage.listeners2["t2"]) == 0
        assert square_minus_one.value == 35
        assert len(square.result._storage.listeners2["t2"]) == 1
        square_minus_one._auto_subscriber.value.reactive_used == {square.value}

    with context1:
        assert r1 is square.result
        assert len(square.result._storage.listeners2["t1"]) == 1
        square._last_finished_event = None  # type: ignore
        square_minus_one._auto_subscriber.value.reactive_used == {square.value}
        assert square_minus_one.value == 24
        square(7)
        square_minus_one._auto_subscriber.value.reactive_used == {square.value}
        assert square._last_finished_event  # type: ignore
        square._last_finished_event.wait()  # type: ignore
        assert square_minus_one.value == 48

    with context2:
        assert r2 is square.result
        assert square_minus_one.value == 35
        square(8)
        assert square._last_finished_event  # type: ignore
        square._last_finished_event.wait()  # type: ignore
        assert square_minus_one.value == 63


# copied from hooks_test.py


def test_use_task_intrusive_cancel():
    result = None
    last_value = 0
    seconds = 4.0

    @solara.component
    def Test():
        nonlocal result
        nonlocal last_value

        def work():
            nonlocal last_value
            for i in range(100):
                last_value = i
                # if not cancelled, might take 4 seconds
                time.sleep(seconds / 100)
            return 2**42

        result = use_task(work, dependencies=[])
        return w.Label(value="test")

    solara.render_fixed(Test(), handle_error=False)
    assert result is not None
    assert isinstance(result, solara.Result)
    result.cancel()
    while result.state in [solara.ResultState.STARTING, solara.ResultState.RUNNING]:
        time.sleep(0.1)
    assert result.state == solara.ResultState.CANCELLED
    assert last_value != 99

    # also test retry
    seconds = 0.1
    result.retry()
    while result.state == solara.ResultState.CANCELLED:
        time.sleep(0.1)
    while result.state == solara.ResultState.RUNNING:
        time.sleep(0.1)
    assert last_value == 99


async def test_use_task_async():
    result = None
    last_value = 0
    seconds = 4.0

    @solara.component
    def Test():
        nonlocal result
        nonlocal last_value

        async def work():
            nonlocal last_value
            for i in range(100):
                last_value = i
                # if not cancelled, might take 4 seconds
                await asyncio.sleep(seconds / 100)
            return 2**42

        result = use_task(work, dependencies=[])
        return w.Label(value="test")

    solara.render_fixed(Test(), handle_error=False)
    assert result is not None
    assert isinstance(result, solara.Result)
    result.cancel()
    while result.state in [solara.ResultState.STARTING, solara.ResultState.RUNNING]:
        await asyncio.sleep(0.1)
    assert result.state == solara.ResultState.CANCELLED
    assert last_value != 99

    # also test retry
    seconds = 0.1
    result.retry()
    while result.state == solara.ResultState.CANCELLED:
        await asyncio.sleep(0.1)
    while result.state in [solara.ResultState.STARTING, solara.ResultState.RUNNING]:
        await asyncio.sleep(0.1)
    assert last_value == 99
