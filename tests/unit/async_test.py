import asyncio
from typing import Tuple
import solara
from solara.server import kernel_context
from solara.server import kernel
from unittest import mock
import solara.lab

reactive = solara.reactive(0)
test_async_task_setting = solara.reactive(0)
tasks = []  # always keep a reference to an asyncio.Task


@solara.lab.task  # (prefer_threaded=True)
async def multiply_by(value: int):
    result = reactive.value * value

    # we also test that a task created in a new thread
    async def set_in_task():
        test_async_task_setting.value = result

    task = asyncio.create_task(set_in_task())
    tasks.append(task)
    await asyncio.sleep(0.1)  # give the task a chance to run
    await task  # wait for the task to finish
    return result


@mock.patch("solara._using_solara_server", return_value=True)
async def test_async_kernels_basic(_):
    assert _() is True
    kernel1 = kernel.Kernel()
    kernel2 = kernel.Kernel()
    context1 = kernel_context.VirtualKernelContext(id="toestand-1", kernel=kernel1, session_id="session-1")
    context2 = kernel_context.VirtualKernelContext(id="toestand-2", kernel=kernel2, session_id="session-2")

    values = solara.Reactive[Tuple[int, ...]]((1,))

    async def task1():
        async with context1:
            for i in range(99):
                values.value = values.value + (len(values.value),)
                await asyncio.sleep(0.01)

    async def task2():
        async with context2:
            for i in range(99):
                values.value = values.value + (len(values.value),)
                await asyncio.sleep(0.01)

    # await asyncio.gather(asyncio.create_task(task1(), name="test-task1"), asyncio.create_task(task2(), name="test-task2"))
    await asyncio.gather(task1(), task2())
    assert values.value == (1,)
    with context1:
        assert len(values.value) == 100
        assert values.value[-1] == 99
    with context2:
        assert len(values.value) == 100
        assert values.value[-1] == 99
    assert values.value == (1,)
    async with context1:
        assert len(values.value) == 100
        assert values.value[-1] == 99
    async with context2:
        assert len(values.value) == 100
        assert values.value[-1] == 99
    assert values.value == (1,)


@mock.patch("solara._using_solara_server", return_value=True)
async def test_async_kernels_complex(_):
    assert _() is True
    event1 = asyncio.Event()  # after event, global is 1
    event2 = asyncio.Event()  # after event, global is still 1
    event3 = asyncio.Event()  # after event, global is 2
    event4 = asyncio.Event()  # after event, global is 3
    event5 = asyncio.Event()  # after event, global is 3
    kernel1 = kernel.Kernel()
    kernel2 = kernel.Kernel()
    context1 = kernel_context.VirtualKernelContext(id="toestand-1", kernel=kernel1, session_id="session-1")
    context2 = kernel_context.VirtualKernelContext(id="toestand-2", kernel=kernel2, session_id="session-2")

    main_thread_key = kernel_context.get_current_thread_key()

    async def task1():
        # global default scope
        reactive.value = 1
        event1.set()
        async with context1:
            # kernel scope
            reactive.value = 100
            assert reactive.value == 100
            await event3.wait()
            assert reactive.value == 100
            multiply_by(3)  # result should be 300

    async def task2():
        await event2.wait()
        # global default scope
        assert reactive.value == 1
        reactive.value = 2
        multiply_by(8)  # result should be 16
        event3.set()
        assert kernel_context.get_current_thread_key() == main_thread_key
        async with context2:
            assert main_thread_key in kernel_context.get_current_thread_key() and len(kernel_context.get_current_thread_key()) > len(main_thread_key)
            # kernel scope
            assert reactive.value == 0  # still the default value
            reactive.value = 200
            event4.set()
            multiply_by(3)  # result should be 600

        assert kernel_context.get_current_thread_key() == main_thread_key
        await event5.wait()
        assert reactive.value == 3

    async def test():
        await event1.wait()
        assert reactive.value == 1
        event2.set()
        await event2.wait()
        # still global default scope
        assert reactive.value == 1
        await event3.wait()
        assert reactive.value == 2
        await event4.wait()
        await multiply_by.current_future  # type: ignore
        reactive.value = 3
        event5.set()

    await asyncio.gather(task1(), task2(), test())

    with context1:
        assert reactive.value == 100
    with context2:
        assert reactive.value == 200
    assert reactive.value == 3

    # checking task results
    while not multiply_by.result.finished:
        await asyncio.sleep(0.1)
    assert multiply_by.result.value == 16
    assert test_async_task_setting.value == 16
    with context1:
        while not multiply_by.result.finished:
            await asyncio.sleep(0.1)
        assert multiply_by.result.value == 300
        assert test_async_task_setting.value == 300
    with context2:
        while not multiply_by.result.finished:
            await asyncio.sleep(0.1)
        assert multiply_by.result.value == 600
        assert test_async_task_setting.value == 600


@mock.patch("solara._using_solara_server", return_value=True)
async def test_async_kernels_task(_):
    assert _() is True
    kernel1 = kernel.Kernel()
    context1 = kernel_context.VirtualKernelContext(id="toestand-1", kernel=kernel1, session_id="session-1")

    main_thread_key = kernel_context.get_current_thread_key()

    async with context1:
        assert main_thread_key != kernel_context.get_current_thread_key()
        assert "task" in kernel_context.get_current_thread_key()
        reactive.value = 100
        multiply_by(3)  # result should be 300
        assert reactive.value == 100
        await multiply_by.current_future  # type: ignore
        assert test_async_task_setting.value == 300, "if this fails, the solara task was using the global context"
