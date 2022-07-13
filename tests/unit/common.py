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
