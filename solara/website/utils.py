import inspect
import textwrap


def sig(f):
    lines = inspect.getsourcelines(f)[0]
    end = [k.endswith(":\n") for k in lines].index(True)
    lines = lines[: end + 1]
    return "".join(lines)


def apidoc(f):

    doclines = f.__doc__.split("\n")
    first = doclines[0].strip()
    rest = "\n".join(doclines[1:])  # .strip()
    return f"""
{first}

```python
{sig(f)}
    ...
```


{textwrap.dedent(rest)}
"""
