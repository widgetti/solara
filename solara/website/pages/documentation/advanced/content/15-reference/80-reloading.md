---
title: Automatic reloading of source files when developing with Solara
description: Solara automatically detects changes in certain source file types, and hot reloads your application when you save them.
---
# Reloading

## Reloading of Python files

Solara will auto detect if your script or the sourcecode of an imported module has changes. If so, Solara will reload the page.

(*Note: Upgrade to solara 1.14.0 for a fix in hot reloading using `pip install "solara>=1.14.0"`*)

## Reloading of .vue files

The solara server automatically watches all `.vue` files that are used by vue templates (there are some used in solara.components for example).
When a `.vue` file is saved, the widgets get updated automatically, without needing a page reload, aiding rapid development.

## Reloading of CSS files

The [Style component](/documentation/components/advanced/style) accepts a Path as argument, when that is used and the server is in development mode (the default), also
CSS files will be hot reloaded.


## Reloading of other files

A library that reads its own files, such as templates, can ask Solara to watch them (Solara 1.64.0 and later).
Like all reloading, this works only in development mode, the default.

```python
from solara.server.reload import watch_file

# A change reloads the app, like a change to a Python file.
watch_file(template_path)

# A change calls update(path) instead, and the app does not reload.
watch_file(template_path, on_change=update)
```

A reload re-imports the modules of the app itself, but not installed packages.
So read the file from code that runs again after a reload, for example at render time, or from a call in the app's own code.

A file has one `on_change`.
A later call with `on_change` replaces it, and a call without `on_change` keeps it, until the server stops.
`on_change` gets the resolved path, and runs on the file watcher thread without a kernel context.
To update widgets, enter each context in `solara.server.kernel_context.contexts.values()`.
Solara's own `.vue` hot reload works this way.


## Restarting the server after changes to the solara packages


You don't need to care about this feature if you only use solara, this is only relevant for development on solara itself, [see also development instructions](/documentation/advanced/development/setup).

If the `--auto-restart/-a` flag is passed to solara-server and any changes occur in the `solara` package (excluding `solara.webpage`), solara-server will restart. This speeds up development on `solara-server` for developers since you do not
need to manually restart the server in the terminal.

## Disabling reloading

In production mode (pass the `--production` argument to `solara run`) watching of files is disabled, and no reloading of files or vue templates will occur. If you run solara integrated in flask or uvicorn as laid out in [deployment documentation](https://solara.dev/documentation/getting_started/deploying/self-hosted)
