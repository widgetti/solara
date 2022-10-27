import time


def repeat_while_false(f, timeout=1):
    while True:
        result = f()
        if result:
            return
        if timeout is not None:
            if timeout <= 0:
                raise TimeoutError("Timeout")
            timeout -= 0.1
            time.sleep(0.1)
        else:
            time.sleep(0.1)


def repeat_while_true(f, timeout=1):
    repeat_while_false(lambda: not f(), timeout)


def busy_wait_compare(getter, expected, iteration_delay=0.001, max_iterations=1000):
    iterations = 0
    previous_value = None
    while True:
        current_value = getter()
        if current_value != previous_value:
            previous_value = current_value
            iterations = 0
        else:
            iterations += 1
        if iterations > max_iterations:
            raise TimeoutError(f"Timeout, no change in value for {max_iterations} iterations, current value: {current_value}, expected: {expected}")
        time.sleep(0.001)
        if current_value == expected:
            break
