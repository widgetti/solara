# Scopes

## Application scope

Does not exist (yet), although equals process scope when using a single worker. Could be implemented using Redis.

## Worker scope

The scope of a single worker. E.g. all Python imported modules live in this scope, so Solara does not explicitly support this. Your application (when using React elements) will also live in this scope.

```python
import solara as sol
# only load a global dataframe once per worker
if "df" not in solara.scope.worker:
    process_scope["df"] = ....
```

## User scope

Things like shopping carts should go here.

## UI scope

Connected to the life-time of a single browser tab.

## React scope
