# use_memo

```python
def use_memo(
    f: Any,
    dependencies: Any | None = None,
    debug_name: str = None
) -> Any:
    ...
```

`use_memo` stores ([memoize](https://en.wikipedia.org/wiki/Memoization)) the function return on first render, and then excludes it from being re-executed, except when one of the `dependencies` changes. `dependencies` can take the value `None`, in which case dependencies are automatically obtained from nonlocal variables. If an empty list is passed as `dependencies` instead, the function is only executed once over the entire lifetime of the component.

Not to be confused with [memorize](https://solara.dev/api/memoize) which can cache multiple return values and which can be used outside of component.

See also the [Reacton docs](https://reacton.solara.dev/en/latest/api/#use_memo).