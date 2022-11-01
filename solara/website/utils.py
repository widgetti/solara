import inspect
import textwrap


def sig(f):
    lines = inspect.getsourcelines(f)[0]
    end = [k.endswith(":\n") for k in lines].index(True)
    lines = lines[: end + 1]
    return "".join(lines)


def code(f):
    lines = inspect.getsourcelines(f)[0]
    def_end = [k.endswith(":\n") for k in lines].index(True)
    doc_lines = len(f.__doc__.split("\n"))
    lines = lines[: def_end + 1] + lines[def_end + 1 + doc_lines :]

    return "".join(lines)


def apidoc(f, full=False):
    if not f.__doc__:
        return "no docstring"

    doclines = f.__doc__.split("\n")
    first = doclines[0].strip()
    rest = "\n".join(doclines[1:])  # .strip()
    if full:
        return f"""
{first}

```python
{code(f)}
    ...
```


{textwrap.dedent(rest)}
"""
    else:
        return f"""
{first}

```python
{sig(f)}
    ...
```


{textwrap.dedent(rest)}
"""
