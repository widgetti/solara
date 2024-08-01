---
title: The rules of hooks in Solara
description: Learn the rules that govern the usage of hooks in your Solara application.
----
# Rules of hooks

Hooks are Python function whose name start with `use_`. The most used hook is [use_state](https://solara.dev/documentation/api/hooks/use_state) which is used to manage the state of a component.

Hooks can only be called at the top level of a function component or a custom hook. They cannot be called inside loops, conditions, or nested functions.
The reason for this is that hooks rely on the order in which they are called to maintain state between renders. If a hook is called conditionally, it may not be called on every render, which can mix up the states.

```python
import solara


@solara.component
def Page():
    x, set_x = solara.use_state(1)  # state 'slot' 1
    if x < 10:
        y, set_y = solara.use_state(2)  # state 'slot' 2
    else:
        y, set_y = solara.use_state("foo") # *also* state 'slot' 2
    solara.Text("Done")
```

In the above example, the `use_state(2)` and `use_state("foo")` is called conditionally, which means that the state 'slot' 2 (meaning, `y` and `set_y`) sometimes refer to the integer `2` and sometimes to the string `"foo"`. This gives unexpected behavior and will lead to bugs.


The rules of hooks are checked by Solara, if you break the rules, you will get a warning, and in the future (Solara v2.0) you will get an error (an exception is raised).

## Example

```python
import solara


@solara.component
def Page():
    for i in range(10):
        solara.use_state(1)
    solara.Text("Done")
```

Will give the warning:
```
/some/prefix/site-packages/solara/solara/validate_hooks.py:122: UserWarning: /my/app.py:56: Page: `use_state` found within a loop created on line 55
To suppress this check, replace the line with:
                solara.use_state(1)  # noqa: SH103

Make sure you understand the consequences of this, by reading about the rules of hooks at:
    https://solara.dev/documentation/advanced/understanding/rules-of-hooks
```

As the warning suggests, you can suppress the warning by adding `# noqa: SH103` to the line that breaks the rules.

```python
import solara


@solara.component
def Page():
    for i in range(10):
        solara.use_state(1)  # noqa: SH103

    solara.Text("Done")
```

The warning can also be suppressed for the whole component by adding `# noqa: SH103` to the function definition.

```python
import solara


@solara.component
def Page():  # noqa: SH103
    for i in range(10):
        solara.use_state(1)

    solara.Text("Done")
```


However, we strongly advise against this, and you should only use it if you know what you are doing (knowing the the loop will always run a fixed amount of times).

If you want to have an error raised instead of a warning, you can set the environment variable `SOLARA_CHECK_HOOKS=raise`, this is
planned to be the default in Solara v2.0.

In that case, you should get an error like this:

```

solara.validate_hooks.HookValidationError: /my/app.py:56: Page: `use_state` found within a loop created on line 55
To suppress this check, replace the line with:
                solara.use_state(1)  # noqa: SH103

Make sure you understand the consequences of this, by reading about the rules of hooks at:
    https://solara.dev/documentation/advanced/understanding/rules-of-hooks
```


For convenience, you can also disable the check by setting the environment variable `SOLARA_CHECK_HOOKS=off`, but we strongly advise against this.

## Types of error

### Early return (SH101)

```python
import solara


@solara.component
def Page():
     solara.Text("Done")
    if x < 10:
        return  # will cause the below use_state to not always be called
    solara.use_state(1)
```

### Conditional use (SH102)

```python
import solara


@solara.component
def Page():
    if x < 10:
        solara.use_state(1)  # will cause the use_state to not always be called
    solara.Text("Done")
```


### Loop use (SH103)

```python
import solara


@solara.component
def Page():
    for i in range(x):
        solara.use_state(1)  # will cause the use_state to not always be a constant number of times
    solara.Text("Done")
```

### Nested function use (SH104)

```python
import solara


@solara.component
def Page():
    def inner():
        solara.use_state(1)  # will use_state always be called? Difficult to analyze, so don't do it
    inner()
    solara.Text("Done")
```


### Variable assignment (SH105)

```python
import solara


@solara.component
def Page():
    x = solara.use_state
    x(1)  # will use_state always be called? Difficult to analyze, so don't do it
    solara.Text("Done")
```


### Exception use (SH106)

```python
import solara


@solara.component
def Page():
    try:
        this_might_fail()
        solara.use_state(1)  # will use_state always be called? Difficult to analyze, so don't do it
    except:
        pass
    solara.Text("Done")
```

For this reason, it's also advised to always call hooks first, before doing anything else in a function component that might raise
an exception.
